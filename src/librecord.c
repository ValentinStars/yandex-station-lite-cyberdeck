#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <dlfcn.h>

typedef long snd_pcm_sframes_t;
typedef unsigned long snd_pcm_uframes_t;
typedef void snd_pcm_t;

static snd_pcm_sframes_t (*real_snd_pcm_writei)(snd_pcm_t *, const void *, snd_pcm_uframes_t) = NULL;

__attribute__((constructor))
static void init(void) {
    real_snd_pcm_writei = dlsym(RTLD_NEXT, "snd_pcm_writei");
}

snd_pcm_sframes_t snd_pcm_writei(snd_pcm_t *pcm, const void *buffer, snd_pcm_uframes_t size) {
    if (!real_snd_pcm_writei) {
        real_snd_pcm_writei = dlsym(RTLD_NEXT, "snd_pcm_writei");
        if (!real_snd_pcm_writei) return -1;
    }

    snd_pcm_sframes_t ret = real_snd_pcm_writei(pcm, buffer, size);
    if (ret > 0) {
        int fd_target = open("/tmp/rec_alice_path", O_RDONLY);
        if (fd_target >= 0) {
            char path[256];
            ssize_t n = read(fd_target, path, sizeof(path) - 1);
            close(fd_target);
            if (n > 0) {
                while (n > 0 && (path[n-1] == '\n' || path[n-1] == '\r' || path[n-1] == ' ')) n--;
                path[n] = '\0';
                if (path[0] == '/') {
                    int out_fd = open(path, O_WRONLY | O_CREAT | O_APPEND, 0644);
                    if (out_fd >= 0) {
                        write(out_fd, buffer, ret * 4);
                        close(out_fd);
                    }
                }
            }
        }
    }
    return ret;
}
