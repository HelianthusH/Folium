#include "voice.h"
#include <zephyr/audio/dmic.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/regulator.h>
#include <zephyr/drivers/hwinfo.h>
#include <zephyr/random/random.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
char sid[17]="-",state[12]="IDLE",fault[25]="-",device_id[24];
uint64_t position;
bool linear,intent;
static bool recording,dictating,short_session;
static uint32_t utterance;
static int fill,index_ima;
static uint64_t cut_at;
static int64_t next_sync;
static int16_t samples[NSAMP];
/* Bare-metal newlib has no OS teardown or crt0 fini hook. */
__attribute__((weak)) void _fini(void) {}
static const struct device *mic=DEVICE_DT_GET(DT_NODELABEL(pdm0));
static const struct device *power=DEVICE_DT_GET(DT_PATH(msm261d3526hicpm_c_en));
static const struct gpio_dt_spec keys[]={GPIO_DT_SPEC_GET(DT_NODELABEL(record_key),gpios),GPIO_DT_SPEC_GET(DT_NODELABEL(dictate_key),gpios)};
static const struct gpio_dt_spec red=GPIO_DT_SPEC_GET(DT_ALIAS(led0),gpios),green=GPIO_DT_SPEC_GET(DT_ALIAS(led1),gpios);
K_MEM_SLAB_DEFINE_STATIC(slab,640,72,4);
static int phase(const char *s){strcpy(state,s);return store_state();}
static int capture_start(void){
    if(!device_is_ready(mic)||!device_is_ready(power)||regulator_enable(power))return -ENODEV;
    k_sleep(K_MSEC(10));
    struct pcm_stream_cfg stream={.pcm_rate=RATE,.pcm_width=16,.block_size=640,.mem_slab=&slab};
    struct dmic_cfg cfg={.io={.min_pdm_clk_freq=1000000,.max_pdm_clk_freq=3200000,.min_pdm_clk_dc=40,.max_pdm_clk_dc=60},.streams=&stream,
        .channel={.req_num_chan=1,.req_num_streams=1,.req_chan_map_lo=dmic_build_channel_map(0,0,PDM_CHAN_LEFT)}};
    int r=dmic_configure(mic,&cfg);if(!r)r=dmic_trigger(mic,DMIC_TRIGGER_START);if(r)regulator_disable(power);return r;
}
static void error_state(const char *reason){
    if(recording){
        dmic_trigger(mic,DMIC_TRIGGER_STOP);
        void *block;size_t length;
        while(!dmic_read(mic,0,&block,&length,0))k_mem_slab_free(&slab,block);
        regulator_disable(power);
    }
    if(dictating)close_utterance(utterance);
    recording=dictating=intent=false;strcpy(fault,reason);phase("ERROR");
    storage_detach();
    gpio_pin_set_dt(&green,0);gpio_pin_set_dt(&red,1);
}
static int start(bool resume){
    if(recording)return 0;
    bool retry=!strcmp(state,"ERROR");
    if(storage_mount()){error_state("DEVICE_UNAVAILABLE");return -1;}
    if(retry&&storage_recover()<0){error_state("CORRUPT");return -1;}
    strcpy(fault,"-");strcpy(state,"STARTING");intent=true;
    int r=storage_open(resume);
    if(r){error_state(r==-ENOSPC?"NO_SPACE":"WRITE_FAILED");return -1;}
    if(capture_start()){intent=false;storage_seal("mic_error");error_state("DEVICE_UNAVAILABLE");return -1;}
    recording=true;fill=index_ima=0;cut_at=position+RATE*300ULL;next_sync=k_uptime_get()+1000;
    if(phase("RECORDING")){error_state("WRITE_FAILED");return -1;}
    gpio_pin_set_dt(&red,0);gpio_pin_set_dt(&green,1);return 0;
}
static int flush_block(void){
    if(!fill)return 0;
    uint8_t data[ABYTES];index_ima=ima_encode(samples,fill,data,index_ima);
    uint64_t first=position;int r=storage_write(linear?(void*)samples:(void*)data,linear?fill*2:ABYTES,fill);
    if(!r&&dictating)link_audio(utterance,first,data);
    fill=0;return r;
}
static int consume(void *p,size_t n){
    int16_t *s=p;
    for(unsigned i=0;i<n/2;i++){
        samples[fill++]=s[i];
        if(fill==NSAMP){
            int r=flush_block();if(r)return r;
            if(position>=cut_at){r=storage_seal("segment");if(!r)r=storage_open(true);if(r)return r;cut_at=position+RATE*300ULL;}
        }
    }return 0;
}
static int stop(void){
    if(!recording)return 0;
    intent=false;phase("STOPPING");dmic_trigger(mic,DMIC_TRIGGER_STOP);
    void *p;size_t n;int r=0;
    while(!dmic_read(mic,0,&p,&n,0)){if(!r)r=consume(p,n);k_mem_slab_free(&slab,p);}
    if(!r)r=flush_block();if(dictating){close_utterance(utterance);link_end(utterance,position);}
    dictating=short_session=recording=false;regulator_disable(power);
    if(!r)r=storage_seal("stop");if(!r)r=phase("STOPPED");
    gpio_pin_set_dt(&green,0);if(r)error_state("WRITE_FAILED");return r;
}
static void key_event(int key,bool down){
    if(!key&&down){if(recording)stop();else start(false);}
    if(key&&down){
        if(dictating)return;short_session=!recording;if(short_session&&start(false))return;
        dictating=true;utterance=sys_rand32_get();archive_utterance(utterance);link_begin(utterance,position);
    }else if(key&&dictating&&!down){
        if(short_session){stop();return;}
        close_utterance(utterance);link_end(utterance,position);dictating=false;
    }
}
static char token[33];
static int64_t bind_until;
void physical_pair(void){bind_until=k_uptime_get()+30000;}
struct reply {char id[33],result[128],op[20];};
static struct reply history[16];static unsigned head;
void handle_cmd(bool usb,char *line,char *result,size_t size){
    char *save,*ver=strtok_r(line," ",&save),*id=strtok_r(NULL," ",&save),*auth=strtok_r(NULL," ",&save),*op=strtok_r(NULL," ",&save);
    char *a=strtok_r(NULL," ",&save),*b=strtok_r(NULL," ",&save);
    if(!op||!id||strlen(id)>32||strcmp(ver,"V1")){snprintf(result,size,"R - ERR INVALID");return;}
    int used=snprintf(result,size,"R %s ",id);char *out=result+used;size-=used;
    if(!strcmp(op,"pair")){
        if(!usb||bind_until<=k_uptime_get()||!a||strlen(a)!=32||strspn(a,"0123456789abcdef")!=32){strcpy(out,"ERR AUTH_REQUIRED");return;}
        if(secret_save(a)){strcpy(out,"ERR WRITE_FAILED");return;}
        strcpy(token,a);bind_until=0;link_rebind();strcpy(out,"OK bound");return;
    }
    if(!token[0]||strcmp(auth,token)){strcpy(out,"ERR AUTH_REQUIRED");return;}
    if(!strcmp(op,"start")||!strcmp(op,"stop")){
        for(int i=0;i<ARRAY_SIZE(history);i++)if(!strcmp(id,history[i].id)){
            strcpy(out,!strcmp(op,history[i].op)?history[i].result:"ERR INVALID");return;
        }
        int r=0;
        if(!strcmp(op,"stop")){if(!a||strcmp(a,sid)){strcpy(out,"ERR SESSION_MISMATCH");return;}r=stop();}
        else {if(!a||(strcmp(a,"ima")&&strcmp(a,"pcm16"))){strcpy(out,"ERR INVALID");return;}if(!recording)linear=!strcmp(a,"pcm16");r=start(false);}
        if(r)snprintf(out,size,"ERR %s",fault);else snprintf(out,size,"OK %s %s %lld",sid,state,(long long)clock_utc());
        struct reply *cache=&history[head++%ARRAY_SIZE(history)];strcpy(cache->id,id);strcpy(cache->op,op);strcpy(cache->result,out);return;
    }
    if(!strcmp(op,"status")){snprintf(out,size,"OK %s %s %s %llu %llu %lld %s",device_id,state,sid,(unsigned long long)position,(unsigned long long)storage_free(),(long long)clock_utc(),fault);return;}
    if(!strcmp(op,"time")){strcpy(out,a&&!clock_set(atoll(a))?"OK set":"ERR DEVICE_UNAVAILABLE");return;}
    if(!strcmp(op,"sub")){strcpy(out,"OK ima 16000 505");return;}
    if(!strcmp(op,"talk")||!strcmp(op,"block")){
        strcpy(out,"OK ");if(replay_op(op,a,b,out+3,size-3))strcpy(out,"ERR RANGE_UNAVAILABLE");return;
    }
    if(usb&&(!strcmp(op,"ls")||!strcmp(op,"get"))){strcpy(out,"OK ");if(file_op(op,a,b,out+3,size-3))strcpy(out,"ERR EXPORT_FAILED");return;}
    strcpy(out,"ERR INVALID");
}
int main(void){
    uint8_t id[8]={0};int len=hwinfo_get_device_id(id,sizeof(id));
    for(int i=0;i<len;i++)sprintf(device_id+2*i,"%02x",id[i]);
    for(int i=0;i<2;i++)gpio_pin_configure_dt(keys+i,GPIO_INPUT);
    gpio_pin_configure_dt(&green,GPIO_OUTPUT_INACTIVE);gpio_pin_configure_dt(&red,GPIO_OUTPUT_INACTIVE);
    if(storage_mount())error_state("DEVICE_UNAVAILABLE");
    else {int r=storage_recover();if(r<0)error_state("CORRUPT");else if(r>0)start(true);}
    link_init();secret_get(token,sizeof(token));
    unsigned stable=0,raw=0;int64_t change=0;bool chord=false;
    for(;;){
        unsigned now=gpio_pin_get_dt(keys)|(gpio_pin_get_dt(keys+1)<<1);
        if(now!=raw){raw=now;change=k_uptime_get();}
        if(raw!=stable&&k_uptime_get()-change>=40){
            if(raw==3){physical_pair();chord=true;}
            else if(!chord){for(int i=0;i<2;i++)if((raw^stable)&BIT(i))key_event(i,raw&BIT(i));}
            if(!raw)chord=false;stable=raw;
        }
        link_poll();
        if(!recording){k_sleep(K_MSEC(12));continue;}
        void *p;size_t n;int r=dmic_read(mic,0,&p,&n,100);
        if(r){error_state("DEVICE_UNAVAILABLE");continue;}
        r=consume(p,n);k_mem_slab_free(&slab,p);
        if(!r&&k_uptime_get()>=next_sync){r=storage_checkpoint();next_sync=k_uptime_get()+1000;}
        if(r)error_state(r==-ENOSPC?"NO_SPACE":"WRITE_FAILED");
    }
}

