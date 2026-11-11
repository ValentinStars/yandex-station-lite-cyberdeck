#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dlfcn.h>

typedef long snd_pcm_sframes_t;
typedef unsigned long snd_pcm_uframes_t;
typedef void snd_pcm_t;

static snd_pcm_sframes_t (*real_snd_pcm_readi)(snd_pcm_t *, void *, snd_pcm_uframes_t) = NULL;

__attribute__((constructor))
static void init(void) {
    real_snd_pcm_readi = dlsym(RTLD_NEXT, "snd_pcm_readi");
}

snd_pcm_sframes_t snd_pcm_readi(snd_pcm_t *pcm, void *buffer, snd_pcm_uframes_t size) {
    if (!real_snd_pcm_readi) {
        real_snd_pcm_readi = dlsym(RTLD_NEXT, "snd_pcm_readi");
        if (!real_snd_pcm_readi) {
            return -1;
        }
    }

    snd_pcm_sframes_t ret = real_snd_pcm_readi(pcm, buffer, size);
    if (ret > 0 && access("/tmp/hard_mic_mute", F_OK) == 0) {
        // Zero out captured audio data completely
        // Assuming max 4 channels, 32-bit (4 bytes per sample), ret * 16 bytes is safe ceiling
        memset(buffer, 0, ret * 16);
    }
    return ret;
}
