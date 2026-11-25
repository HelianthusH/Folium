#include "voice.h"
#include <zephyr/drivers/i2c.h>
#include <zephyr/sys/timeutil.h>
#include <time.h>
static const struct device *bus=DEVICE_DT_GET(DT_NODELABEL(i2c1));
static int dec(int b){return (b>>4)*10+(b&15);}
static int bcd(int n){return ((n/10)<<4)+(n%10);}
int64_t clock_utc(void){
    uint8_t r[7];
    if(!device_is_ready(bus)||i2c_burst_read(bus,0x51,2,r,7)||(r[0]&128))return 0;
    struct tm t={.tm_sec=dec(r[0]&127),.tm_min=dec(r[1]&127),.tm_hour=dec(r[2]&63),.tm_mday=dec(r[3]&63),.tm_mon=dec(r[5]&31)-1,.tm_year=100+dec(r[6])};
    if(t.tm_year<124||t.tm_mon<0||t.tm_mon>11||t.tm_mday<1||t.tm_mday>31||t.tm_hour>23||t.tm_min>59||t.tm_sec>59)return 0;
    return timeutil_timegm64(&t);
}
int clock_set(int64_t epoch){
    if(epoch<1704067200LL||epoch>=4102444800LL)return -EINVAL;
    time_t tt=epoch;struct tm t;gmtime_r(&tt,&t);
    uint8_t r[]={2,bcd(t.tm_sec),bcd(t.tm_min),bcd(t.tm_hour),bcd(t.tm_mday),t.tm_wday,bcd(t.tm_mon+1),bcd(t.tm_year-100)};
    return i2c_write(bus,r,sizeof(r),0x51);
}

