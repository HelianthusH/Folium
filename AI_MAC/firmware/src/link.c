#include "voice.h"
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/usb/usb_device.h>
#include <zephyr/settings/settings.h>
#include <zephyr/sys/crc.h>
#include <zephyr/sys/base64.h>
#include <zephyr/sys/ring_buffer.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define UUID(n) BT_UUID_DECLARE_128(BT_UUID_128_ENCODE(0x4cb30000+(n),0x7873,0x46d7,0x884a,0xb66c77636431ULL))
static const struct device *cdc=DEVICE_DT_GET(DT_NODELABEL(board_cdc_acm_uart));
static struct bt_conn *peer;
static atomic_t pair_deadline;
static enum bt_security_err accept_pair(struct bt_conn *c, const struct bt_conn_pairing_feat *const features){
    uint32_t deadline=(uint32_t)atomic_get(&pair_deadline);
    return deadline && (int32_t)(deadline-k_uptime_get_32())>0 ? BT_SECURITY_ERR_SUCCESS : BT_SECURITY_ERR_PAIR_NOT_ALLOWED;
}
static struct bt_conn_auth_cb auth_callbacks={.pairing_accept=accept_pair};
void link_rebind(void){
    bt_unpair(BT_ID_DEFAULT,BT_ADDR_LE_ANY);
    atomic_set(&pair_deadline,(atomic_val_t)(k_uptime_get_32()+120000));
}
static void paired(struct bt_conn *conn,bool bonded){atomic_clear(&pair_deadline);}
static struct bt_conn_auth_info_cb pair_info={.pairing_complete=paired};
static bool sub_usb,sub_ble;
K_MUTEX_DEFINE(peer_lock);
struct cmd {bool usb;char text[180];};
K_MSGQ_DEFINE(requests,sizeof(struct cmd),6,4);
struct parser {char line[180];size_t count;bool overflow;};
static struct parser parsers[2];
static void feed(bool usb,const uint8_t *p,size_t len){
    struct parser *s=&parsers[usb];
    for(size_t i=0;i<len;i++){
        if(p[i]=='\n'){if(!s->overflow&&s->count){struct cmd q={.usb=usb};memcpy(q.text,s->line,s->count);k_msgq_put(&requests,&q,K_NO_WAIT);}s->count=0;s->overflow=false;}
        else if(s->count<sizeof(s->line)-1)s->line[s->count++]=p[i];else s->overflow=true;
    }
}
static ssize_t control(struct bt_conn *c,const struct bt_gatt_attr *a,const void *b,uint16_t len,uint16_t off,uint8_t flags){
    if(off)return BT_GATT_ERR(BT_ATT_ERR_INVALID_OFFSET);feed(false,b,len);return len;
}
BT_GATT_SERVICE_DEFINE(service,BT_GATT_PRIMARY_SERVICE(UUID(0)),
    BT_GATT_CHARACTERISTIC(UUID(1),BT_GATT_CHRC_WRITE,BT_GATT_PERM_WRITE_ENCRYPT,NULL,control,NULL),
    BT_GATT_CHARACTERISTIC(UUID(2),BT_GATT_CHRC_NOTIFY,BT_GATT_PERM_NONE,NULL,NULL,NULL),
    BT_GATT_CCC(NULL,BT_GATT_PERM_READ_ENCRYPT|BT_GATT_PERM_WRITE_ENCRYPT));
static struct bt_data ads[]={BT_DATA_BYTES(BT_DATA_FLAGS,BT_LE_AD_GENERAL|BT_LE_AD_NO_BREDR),BT_DATA(BT_DATA_NAME_COMPLETE,"VoiceCard",9)};
static void advertise(struct k_work *w){bt_le_adv_start(BT_LE_ADV_CONN_FAST_1,ads,ARRAY_SIZE(ads),NULL,0);}
K_WORK_DEFINE(adv_work,advertise);
static void connected(struct bt_conn *c,uint8_t err){
    if(err)return;k_mutex_lock(&peer_lock,K_FOREVER);peer=bt_conn_ref(c);sub_ble=false;k_mutex_unlock(&peer_lock);
}
static void disconnected(struct bt_conn *c,uint8_t why){
    k_mutex_lock(&peer_lock,K_FOREVER);if(peer){bt_conn_unref(peer);peer=NULL;}sub_ble=false;memset(&parsers[0],0,sizeof(parsers[0]));k_mutex_unlock(&peer_lock);
}
static void recycled(void){k_work_submit(&adv_work);}
BT_CONN_CB_DEFINE(callbacks)={.connected=connected,.disconnected=disconnected,.recycled=recycled};
RING_BUF_DECLARE(tx,8192);
static void irq(const struct device *dev,void *unused){
    uart_irq_update(dev);
    if(uart_irq_rx_ready(dev)){uint8_t b[64];int n;while((n=uart_fifo_read(dev,b,sizeof(b)))>0)feed(true,b,n);}
    if(uart_irq_tx_ready(dev)){uint8_t *p;unsigned n=ring_buf_get_claim(&tx,&p,64);
        if(n){int sent=uart_fifo_fill(dev,p,n);ring_buf_get_finish(&tx,MAX(sent,0));}else uart_irq_tx_disable(dev);}
}
struct packet {bool usb;char data[1050];};
K_MSGQ_DEFINE(packets,sizeof(struct packet),8,4);
static void sender(void *a,void *b,void *d){
    struct packet pkt;
    for(;;){
        k_msgq_get(&packets,&pkt,K_FOREVER);size_t n=strlen(pkt.data);
        if(pkt.usb){unsigned key=irq_lock();if(ring_buf_space_get(&tx)>=n){ring_buf_put(&tx,pkt.data,n);uart_irq_tx_enable(cdc);}irq_unlock(key);continue;}
        k_mutex_lock(&peer_lock,K_FOREVER);struct bt_conn *c=peer?bt_conn_ref(peer):NULL;k_mutex_unlock(&peer_lock);
        if(c){size_t mtu=bt_gatt_get_mtu(c)-3;
            for(size_t i=0;i<n;i+=mtu)if(bt_gatt_notify(c,&service.attrs[4],pkt.data+i,MIN(mtu,n-i)))break;
            bt_conn_unref(c);
        }
    }
}
K_THREAD_DEFINE(tx_thread,3000,sender,NULL,NULL,NULL,5,0,0);
static void post(bool usb,const char *line){struct packet p={.usb=usb};snprintf(p.data,sizeof(p.data),"\n%s\n",line);k_msgq_put(&packets,&p,K_NO_WAIT);}
static int load_token(const char *key,size_t len,settings_read_cb read,void *arg,void *param){
    if(!key&&len==32)return read(arg,param,32)==32?0:-EIO;return 0;
}
int secret_get(char *s,size_t n){return settings_load_subtree_direct("voice/token",load_token,s);}
int secret_save(const char *s){sub_ble=sub_usb=false;return settings_save_one("voice/token",s,32);}
int link_init(void){
    int r=usb_enable(NULL);uart_irq_callback_user_data_set(cdc,irq,NULL);uart_irq_rx_enable(cdc);
    if(!bt_enable(NULL)){bt_conn_auth_cb_register(&auth_callbacks);bt_conn_auth_info_cb_register(&pair_info);settings_load();k_work_submit(&adv_work);}return r;
}
void link_poll(void){
    struct cmd q;char result[1024];uint32_t dtr=0;
    if(!uart_line_ctrl_get(cdc,UART_LINE_CTRL_DTR,&dtr)&&!dtr)sub_usb=false;
    if(k_msgq_get(&requests,&q,K_NO_WAIT))return;
    handle_cmd(q.usb,q.text,result,sizeof(result));
    if(strstr(result," OK ima 16000 505")){if(q.usb)sub_usb=true;else sub_ble=true;}
    post(q.usb,result);
}
void link_audio(uint32_t utt,uint64_t first,const uint8_t *data){
    if(!sub_usb&&!sub_ble)return;
    char line[465];size_t n;int k=snprintf(line,sizeof(line),"A %s %08x %llu %08x ",sid,utt,(unsigned long long)first,crc32_ieee(data,ABYTES));
    base64_encode(line+k,sizeof(line)-k,&n,data,ABYTES);line[k+n]=0;
    if(sub_usb)post(true,line);if(sub_ble)post(false,line);
}
void link_end(uint32_t utt,uint64_t first){
    char line[80];snprintf(line,sizeof(line),"E %s %08x %llu",sid,utt,(unsigned long long)first);
    if(sub_usb)post(true,line);if(sub_ble)post(false,line);
}
void link_begin(uint32_t utt,uint64_t first){
    char line[80];snprintf(line,sizeof(line),"B %s %08x %llu",sid,utt,(unsigned long long)first);
    if(sub_usb)post(true,line);if(sub_ble)post(false,line);
}

