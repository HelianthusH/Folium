#include "voice.h"
#include <zephyr/fs/fs.h>
#include <zephyr/storage/disk_access.h>
#include <zephyr/sys/crc.h>
#include <zephyr/sys/base64.h>
#include <zephyr/random/random.h>
#include <mbedtls/sha256.h>
#include <ff.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <ctype.h>
static FATFS fat;
static struct fs_mount_t mountpoint={.type=FS_FATFS,.mnt_point="/SD:",.fs_data=&fat,.flags=FS_MOUNT_FLAG_NO_FORMAT};
static struct fs_file_t wav;
static bool mounted,opened;
static uint8_t io[4096];
static char leased[PATHLEN];
static int64_t lease_until;
struct journal {
    uint32_t version,seq;
    char directory[80],id[17],phase[12],error[25];
    uint32_t part,bytes,samples,rolling;
    uint64_t first;
    int64_t utc;
    uint8_t pcm,want,pending;
    uint32_t crc;
};
static struct journal j;
/* The most recent push-to-talk ranges refer to the original WAV blocks. */
#define TALK_SLOTS 16
#define SEG_SAMPLES (((300U*RATE+NSAMP-1)/NSAMP)*NSAMP)
struct talk_range {
    char uid[26],dir[80];
    uint64_t begin,end,part_first;
    uint32_t part;
    bool pcm,closed;
};
static struct talk_range talks[TALK_SLOTS];
static unsigned talk_count;
void archive_utterance(uint32_t id){
    struct talk_range *t=&talks[talk_count++%TALK_SLOTS];
    snprintf(t->uid,sizeof(t->uid),"%s-%08x",sid,id);
    strcpy(t->dir,j.directory);
    t->begin=position;t->end=position;t->part_first=j.first;t->part=j.part;t->pcm=linear;t->closed=false;
}
void close_utterance(uint32_t id){
    if(talk_count){struct talk_range *t=&talks[(talk_count-1)%TALK_SLOTS];t->end=position;t->closed=true;}
}
int replay_op(const char *op,const char *uid,const char *sample,char *out,size_t cap){
    if(!talk_count)return -ENOENT;
    struct talk_range *t=NULL;
    if(!uid||!strcmp(uid,"latest"))t=&talks[(talk_count-1)%TALK_SLOTS];
    else for(unsigned i=0;i<TALK_SLOTS;i++)if(!strcmp(talks[i].uid,uid)){t=&talks[i];break;}
    if(!t)return -ENOENT;
    uint64_t end=t->closed?t->end:position;
    if(!strcmp(op,"talk")){
        snprintf(out,cap,"%s %llu %llu %u",t->uid,(unsigned long long)t->begin,(unsigned long long)end,t->closed);
        return 0;
    }
    if(!sample||!*sample||strspn(sample,"0123456789")!=strlen(sample))return -EINVAL;
    uint64_t pos=strtoull(sample,NULL,10);
    if(pos<t->begin||pos>=end||(pos-t->begin)%NSAMP)return -ERANGE;
    uint64_t relative=pos-t->part_first;
    unsigned part=t->part+relative/SEG_SAMPLES;
    uint32_t within=relative%SEG_SAMPLES;
    bool active=opened&&part==j.part&&!strcmp(t->dir,j.directory);
    char path[PATHLEN];snprintf(path,sizeof(path),"%s/%04u.%s",t->dir,part,active?"part":"wav");
    struct fs_file_t reader;fs_file_t_init(&reader);
    struct fs_file_t *f=active?&wav:&reader;
    off_t saved=0;
    if(active){saved=fs_tell(f);if(saved<0)return -EIO;}
    else if(fs_open(f,path,FS_O_READ))return -ENOENT;
    int16_t pcm[NSAMP];uint8_t encoded[ABYTES];
    unsigned count=MIN((uint64_t)NSAMP,end-pos);
    size_t len=t->pcm?2*count:ABYTES;
    off_t at=t->pcm?44+within*2:60+(within/NSAMP)*ABYTES;
    int r=fs_seek(f,at,FS_SEEK_SET);
    if(!r&&fs_read(f,t->pcm?(void*)pcm:(void*)encoded,len)!=(ssize_t)len)r=-EIO;
    if(active){if(fs_seek(f,saved,FS_SEEK_SET))r=-EIO;}else fs_close(f);
    if(r)return r;
    if(t->pcm)ima_encode(pcm,count,encoded,0);
    size_t n;int prefix=snprintf(out,cap,"%08x ",crc32_ieee(encoded,ABYTES));
    if(base64_encode(out+prefix,cap-prefix,&n,encoded,ABYTES))return -EIO;
    out[prefix+n]=0;return 0;
}
void storage_detach(void){
    if(opened){fs_close(&wav);opened=false;}
    if(mounted && !fs_unmount(&mountpoint))mounted=false;
    if(!mounted){memset(&j,0,sizeof(j));talk_count=0;memset(talks,0,sizeof(talks));}
}
static char pathname[PATHLEN];
static void path_for(char *p,const char *ext){snprintf(p,PATHLEN,"%s/%04u.%s",j.directory,j.part,ext);}
static int ensure_dir(char *s){
    struct fs_dirent e;
    if(!fs_stat(s,&e))return e.type==FS_DIR_ENTRY_DIR?0:-ENOTDIR;
    return fs_mkdir(s);
}
static int file_put(const char *p,const void *data,size_t n){
    struct fs_file_t f;fs_file_t_init(&f);
    int r=fs_open(&f,p,FS_O_CREATE|FS_O_WRITE|FS_O_TRUNC);if(r)return r;
    r=fs_write(&f,data,n)==n?fs_sync(&f):-EIO;int c=fs_close(&f);return r?r:c;
}
int store_state(void){
    if(!mounted)return -ENODEV;
    j.version=1;j.seq++;j.pcm=linear;j.want=intent;
    snprintf(j.phase,sizeof(j.phase),"%s",state);snprintf(j.error,sizeof(j.error),"%s",fault);
    j.crc=crc32_ieee((uint8_t*)&j,offsetof(struct journal,crc));
    return file_put((j.seq&1)?"/SD:/VC1.BIN":"/SD:/VC0.BIN",&j,sizeof(j));
}
int storage_mount(void){
    if(mounted)return 0;
    int r=fs_mount(&mountpoint);if(r)return r;
    mounted=true;fs_file_t_init(&wav);return ensure_dir(ROOT);
}
uint64_t storage_free(void){struct fs_statvfs s;return fs_statvfs("/SD:",&s)?0:(uint64_t)s.f_frsize*s.f_bfree;}
struct victim {char path[PATHLEN];int64_t end;};
/* A sealed segment has a small companion retention stamp. Use its end UTC,
   never FAT modification time. Bounded depth matches REC/YYYY/MM/DD/SID. */
static int oldest(const char *folder,int depth,int64_t cutoff,struct victim *v){
    if(depth>4)return 0;
    struct fs_dir_t d;struct fs_dirent e;fs_dir_t_init(&d);
    int r=fs_opendir(&d,folder);if(r)return r;
    while(!(r=fs_readdir(&d,&e))&&e.name[0]){
        char p[PATHLEN];if(snprintf(p,sizeof(p),"%s/%s",folder,e.name)>=(int)sizeof(p))continue;
        if(e.type==FS_DIR_ENTRY_DIR){if(strcmp(e.name,"UNSYNCED")){r=oldest(p,depth+1,cutoff,v);if(r)break;}continue;}
        char *ext=strrchr(p,'.');if(!ext||strcmp(ext,".end"))continue;
        struct fs_file_t f;fs_file_t_init(&f);int64_t end=0;
        if(!fs_open(&f,p,FS_O_READ)){int n=fs_read(&f,&end,sizeof(end));fs_close(&f);if(n!=sizeof(end))continue;}
        strcpy(ext,".wav");
        if(end>0&&end<cutoff&&end<v->end&&!(k_uptime_get()<lease_until&&!strcmp(leased,p))){
            strcpy(v->path,p);v->end=end;
        }
    }
    fs_closedir(&d);return r;
}
int storage_space(void){
    while(storage_free()<512ULL*1024*1024){
        int64_t now=clock_utc();if(!now)return -ENOSPC;
        struct victim v={.end=INT64_MAX};int r=oldest(ROOT,0,now-48*3600,&v);
        if(r)return r;if(!v.path[0])return -ENOSPC;
        r=fs_unlink(v.path);if(r&&r!=-ENOENT)return r;
        char *ext=strrchr(v.path,'.');strcpy(ext,".json");fs_unlink(v.path);strcpy(ext,".end");if(fs_unlink(v.path))return -EIO;
    }
    return 0;
}
int storage_open(bool resume){
    if(opened)return -EBUSY;
    int r=storage_space();if(r)return r;
    if(!resume){
        uint32_t a=sys_rand32_get(),b=sys_rand32_get();
        snprintf(sid,17,"%08x%08x",a,b);strcpy(j.id,sid);
        int64_t now=clock_utc();char date[20]="UNSYNCED";
        if(now){time_t epoch=now;struct tm t;gmtime_r(&epoch,&t);strftime(date,sizeof(date),"%Y/%m/%d",&t);}
        snprintf(j.directory,sizeof(j.directory),ROOT "/%s/%s",date,sid);
        for(char *p=j.directory+strlen(ROOT)+1;*p;p++)if(*p=='/'){*p=0;r=ensure_dir(j.directory);*p='/';if(r)return r;}
        r=fs_mkdir(j.directory);if(r)return r;j.part=0;position=0;
    }
    j.part++;j.first=position;j.bytes=j.samples=j.rolling=0;j.utc=clock_utc();
    path_for(pathname,"part");r=fs_open(&wav,pathname,FS_O_CREATE|FS_O_WRITE|FS_O_READ);
    if(r)return r;opened=true;
    uint8_t h[60];size_t n=wav_header(h,linear,0,0);
    if(fs_write(&wav,h,n)!=n||fs_sync(&wav)){fs_close(&wav);opened=false;return -EIO;}
    j.pending=1;return store_state();
}
int storage_write(const void *data,unsigned bytes,unsigned samples){
    if(!opened||fs_write(&wav,data,bytes)!=bytes)return -EIO;
    j.rolling=crc32_ieee_update(j.rolling,data,bytes);
    j.bytes+=bytes;j.samples+=samples;position+=samples;return 0;
}
int storage_checkpoint(void){return !opened||fs_sync(&wav)?-EIO:store_state();}
int storage_seal(const char *why){
    if(!opened)return 0;
    int r=storage_checkpoint();uint8_t h[60],digest[32];size_t hn=wav_header(h,linear,j.bytes,j.samples);
    if(!r&&(fs_seek(&wav,0,FS_SEEK_SET)||fs_write(&wav,h,hn)!=hn||fs_sync(&wav)||fs_seek(&wav,0,FS_SEEK_SET)))r=-EIO;
    mbedtls_sha256_context sha;mbedtls_sha256_init(&sha);mbedtls_sha256_starts(&sha,0);
    ssize_t n=0;while(!r&&(n=fs_read(&wav,io,sizeof(io)))>0)mbedtls_sha256_update(&sha,io,n);
    if(n<0)r=n;mbedtls_sha256_finish(&sha,digest);mbedtls_sha256_free(&sha);
    if(fs_close(&wav)&&!r)r=-EIO;opened=false;if(r)return r;
    char name[PATHLEN],hex[65],meta[680];path_for(name,"wav");
    for(int i=0;i<32;i++)sprintf(hex+i*2,"%02x",digest[i]);
    int len=snprintf(meta,sizeof(meta),"{\"version\":1,\"firmware\":\"1.0\",\"device_id\":\"%s\",\"session_id\":\"%s\",\"segment\":%u,\"file\":\"%04u.wav\",\"utc\":%lld,\"clock_trusted\":%s,\"codec\":\"%s\",\"rate\":16000,\"channels\":1,\"first_sample\":%llu,\"samples\":%u,\"bytes\":%u,\"sha256\":\"%s\",\"reason\":\"%s\",\"gap_after\":\"%s\"}\n",
        device_id,j.id,j.part,j.part,(long long)j.utc,j.utc?"true":"false",linear?"pcm16":"ima",(unsigned long long)j.first,j.samples,(unsigned)(j.bytes+hn),hex,why,strcmp(why,"power_loss")?"none":"unknown");
    char temp[PATHLEN],final[PATHLEN];path_for(temp,"tmp");path_for(final,"json");
    if((r=file_put(temp,meta,len)))return r;
    if(strcmp(pathname,name)&&(r=fs_rename(pathname,name)))return r;
    if((r=fs_rename(temp,final)))return r;
    int64_t end=j.utc?j.utc+(j.samples+RATE-1)/RATE:0;path_for(temp,"end");
    if((r=file_put(temp,&end,sizeof(end))))return r;
    j.pending=0;return store_state();
}
int storage_recover(void){
    struct journal candidate;
    for(int i=0;i<2;i++){
        struct fs_file_t f;fs_file_t_init(&f);
        if(fs_open(&f,i?"/SD:/VC1.BIN":"/SD:/VC0.BIN",FS_O_READ))continue;
        int n=fs_read(&f,&candidate,sizeof(candidate));fs_close(&f);
        if(n==sizeof(candidate)&&candidate.version==1&&candidate.crc==crc32_ieee((uint8_t*)&candidate,offsetof(struct journal,crc))&&candidate.seq>j.seq)j=candidate;
    }
    if(!j.seq)return 0;
    linear=j.pcm;intent=j.want;strcpy(sid,j.id);position=j.first+j.samples;
    if(!j.pending){strcpy(state,j.phase);strcpy(fault,j.error);return intent?1:0;}
    path_for(pathname,"part");int r=fs_open(&wav,pathname,FS_O_READ|FS_O_WRITE);
    if(r==-ENOENT){path_for(pathname,"wav");r=fs_open(&wav,pathname,FS_O_READ|FS_O_WRITE);}
    if(r)return r;
    size_t hn=linear?44:60;uint32_t crc=0,left=j.bytes;
    if(fs_seek(&wav,hn,FS_SEEK_SET))r=-EIO;
    while(left&&!r){size_t want=MIN(left,sizeof(io));if(fs_read(&wav,io,want)!=want){r=-EBADMSG;break;}crc=crc32_ieee_update(crc,io,want);left-=want;}
    if(crc!=j.rolling)r=-EBADMSG;
    if(!r)r=fs_truncate(&wav,hn+j.bytes);
    if(r){fs_close(&wav);return r;}
    opened=true;r=storage_seal("power_loss");return r?r:(intent?1:0);
}
int file_op(const char *op,const char *rel,const char *offset,char *out,size_t cap){
    if(!rel||!offset||strlen(rel)>75||strstr(rel,"..")||rel[0]=='/'||strspn(rel,"0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ._/")!=strlen(rel))return -EINVAL;
    char p[PATHLEN];snprintf(p,sizeof(p),ROOT "/%s",!strcmp(rel,".")?"":rel);
    unsigned long off=strtoul(offset,NULL,10);
    if(!strcmp(op,"ls")){
        if(!strcmp(rel,"."))strcpy(p,ROOT);
        struct fs_dir_t d;struct fs_dirent e;fs_dir_t_init(&d);int r=fs_opendir(&d,p);if(r)return r;
        do {r=fs_readdir(&d,&e);if(r||!e.name[0])break;}while(off--);
        fs_closedir(&d);if(r)return r;
        if(e.name[0])snprintf(out,cap,"%c %s",e.type==FS_DIR_ENTRY_DIR?'D':'F',e.name);else strcpy(out,"END");return 0;
    }
    char *ext=strrchr(p,'.');if(!ext||(strcmp(ext,".json")&&strcmp(ext,".wav")))return -EINVAL;
    struct fs_file_t f;fs_file_t_init(&f);int r=fs_open(&f,p,FS_O_READ);if(r)return r;
    strcpy(leased,p);lease_until=k_uptime_get()+60000;
    r=fs_seek(&f,off,FS_SEEK_SET);int n=r?r:fs_read(&f,io,720);fs_close(&f);if(n<0)return n;
    size_t used;snprintf(out,cap,"%08x ",crc32_ieee(io,n));if(base64_encode(out+9,cap-9,&used,io,n))return -EIO;out[9+used]=0;return 0;
}

