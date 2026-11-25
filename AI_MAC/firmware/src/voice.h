#pragma once
#include <zephyr/kernel.h>
#include <stdint.h>
#include <stdbool.h>
#include "codec.h"
#define ROOT "/SD:/REC"
#define PATHLEN 110
extern char sid[17], state[12], fault[25], device_id[24];
extern uint64_t position;
extern bool linear, intent;
int64_t clock_utc(void);
int clock_set(int64_t epoch);
int storage_mount(void);
void storage_detach(void);
void archive_utterance(uint32_t id);
void close_utterance(uint32_t id);
int replay_op(const char *op,const char *uid,const char *sample,char *out,size_t cap);
int storage_open(bool resume);
int storage_write(const void *data,unsigned len,unsigned samples);
int storage_seal(const char *reason);
int storage_checkpoint(void);
int storage_recover(void);
int store_state(void);
uint64_t storage_free(void);
int storage_space(void);
int file_op(const char *op,const char *rel,const char *offset,char *out,size_t cap);
int link_init(void);
void link_poll(void);
void link_audio(uint32_t utt,uint64_t first,const uint8_t *data);
void link_end(uint32_t utt,uint64_t first);
void link_begin(uint32_t utt,uint64_t first);
void handle_cmd(bool usb,char *line,char *result,size_t size);
void physical_pair(void);
void link_rebind(void);
int secret_get(char *s,size_t n);
int secret_save(const char *s);

