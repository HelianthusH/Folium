#include "codec.h"
#include <string.h>
static const int steps[89]={7,8,9,10,11,12,13,14,16,17,19,21,23,25,28,31,34,37,41,45,50,55,60,66,73,80,88,97,107,118,130,143,157,173,190,209,230,253,279,307,337,371,408,449,494,544,598,658,724,796,876,963,1060,1166,1282,1411,1552,1707,1878,2066,2272,2499,2749,3024,3327,3660,4026,4428,4871,5358,5894,6484,7132,7845,8630,9493,10442,11487,12635,13899,15289,16818,18500,20350,22385,24623,27086,29794,32767};
static const int adjust[8]={-1,-1,-1,-1,2,4,6,8};
static int clip(int a,int lo,int hi){return a<lo?lo:a>hi?hi:a;}
static void le16(uint8_t *p,uint16_t n){p[0]=n;p[1]=n>>8;}
static void le32(uint8_t *p,uint32_t n){le16(p,n);le16(p+2,n>>16);}
int ima_encode(const int16_t *s,int count,uint8_t out[ABYTES],int ix){
    int pred=s[0]; le16(out,pred); out[2]=ix; out[3]=0;
    for(int i=1;i<NSAMP;i++){
        int delta=(int)s[i<count?i:count-1]-pred;
        int code=delta<0?8:0, step=steps[ix], diff=step>>3;
        if(delta<0)delta=-delta;
        for(int bit=4;bit;bit>>=1,step>>=1){
            if(delta>=step){delta-=step;diff+=step;code|=bit;}
        }
        pred=clip(pred+(code&8?-diff:diff),-32768,32767);
        ix=clip(ix+adjust[code&7],0,88);
        if(i&1)out[4+(i-1)/2]=code;else out[4+(i-1)/2]|=code<<4;
    }
    return ix;
}
size_t wav_header(uint8_t *p,int pcm,uint32_t bytes,uint32_t samples){
    size_t n=pcm?44:60; memset(p,0,n); memcpy(p,"RIFF",4); le32(p+4,bytes+n-8);
    memcpy(p+8,"WAVEfmt ",8);le32(p+16,pcm?16:20);le16(p+20,pcm?1:17);
    le16(p+22,1);le32(p+24,RATE);le32(p+28,pcm?RATE*2:8111);
    le16(p+32,pcm?2:ABYTES);le16(p+34,pcm?16:4);
    if(!pcm){le16(p+36,2);le16(p+38,NSAMP);memcpy(p+40,"fact",4);le32(p+44,4);le32(p+48,samples);}
    memcpy(p+n-8,"data",4);le32(p+n-4,bytes);return n;
}

