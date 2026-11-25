#pragma once
#include <stdint.h>
#include <stddef.h>
#define RATE 16000
#define NSAMP 505
#define ABYTES 256
int ima_encode(const int16_t *pcm, int count, unsigned char out[ABYTES], int index);
size_t wav_header(uint8_t *p, int pcm, uint32_t bytes, uint32_t samples);

