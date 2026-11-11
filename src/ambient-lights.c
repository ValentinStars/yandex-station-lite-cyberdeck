#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <math.h>
#include <signal.h>
#include <time.h>
#include <sys/stat.h>

#define DIFF_NODE "/sys/devices/platform/soc/ffd00000.cbus/ffd1f000.i2c/i2c-0/0-0012/diff"
#define PID_FILE "/var/run/ambient-lights.pid"
#define TOUCH_THRESHOLD 90
#define IDLE_TIMEOUT 5.0

static volatile int running = 1;
static int led_fds[3][3]; // [ring 0..2][r=0, g=1, b=2]
static int diff_fd = -1;

static void on_signal(int sig) {
    (void)sig;
    running = 0;
}

static void all_off(void) {
    for (int z = 0; z < 3; z++) {
        for (int c = 0; c < 3; c++) {
            if (led_fds[z][c] >= 0) {
                pwrite(led_fds[z][c], "0\n", 2, 0);
            }
        }
    }
}

static void set_ring(int z, int r, int g, int b) {
    char buf[16];
    int len;
    
    len = snprintf(buf, sizeof(buf), "%d\n", r);
    pwrite(led_fds[z][0], buf, len, 0);

    len = snprintf(buf, sizeof(buf), "%d\n", g);
    pwrite(led_fds[z][1], buf, len, 0);

    len = snprintf(buf, sizeof(buf), "%d\n", b);
    pwrite(led_fds[z][2], buf, len, 0);
}

static void get_color(float hue_deg, float fade, int *r_out, int *g_out, int *b_out) {
    float h = fmodf(hue_deg, 360.0f);
    if (h < 0.0f) h += 360.0f;
    h /= 60.0f;
    int i = (int)h;
    float f = h - (float)i;
    float r = 0.0f, g = 0.0f, b = 0.0f;

    switch (i) {
        case 0: r = 1.0f; g = f; b = 0.0f; break;
        case 1: r = 1.0f - f; g = 1.0f; b = 0.0f; break;
        case 2: r = 0.0f; g = 1.0f; b = f; break;
        case 3: r = 0.0f; g = 1.0f - f; b = 1.0f; break;
        case 4: r = f; g = 0.0f; b = 1.0f; break;
        default: r = 1.0f; g = 0.0f; b = 1.0f - f; break;
    }

    *r_out = (int)(powf(r, 1.3f) * 255.0f * fade);
    *g_out = (int)(powf(g, 1.6f) * 165.0f * fade);
    *b_out = (int)(powf(b, 1.5f) * 180.0f * fade);
}

static int read_diff(int *c0, int *c1, int *c2) {
    char buf[256];
    if (diff_fd < 0) return -1;
    ssize_t n = pread(diff_fd, buf, sizeof(buf) - 1, 0);
    if (n <= 0) return -1;
    buf[n] = '\0';

    int v0 = 0, v1 = 0, v2 = 0;
    if (sscanf(buf, "DIFF_CH0 = %d\nDIFF_CH1 = %d\nDIFF_CH2 = %d", &v0, &v1, &v2) >= 3) {
        *c0 = v0;
        *c1 = v1;
        *c2 = v2;
        return 0;
    }
    return -1;
}

static double get_time_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}

int main(int argc, char **argv) {
    (void)argc;
    (void)argv;

    // Check / open LED fds
    const char *colors[3] = {"red", "green", "blue"};
    for (int z = 0; z < 3; z++) {
        for (int c = 0; c < 3; c++) {
            char path[128];
            snprintf(path, sizeof(path), "/sys/class/leds/micro:%s:ring%d/brightness", colors[c], z + 1);
            led_fds[z][c] = open(path, O_WRONLY);
            if (led_fds[z][c] < 0) {
                fprintf(stderr, "Failed to open LED: %s\n", path);
            }
        }
    }

    diff_fd = open(DIFF_NODE, O_RDONLY);
    if (diff_fd < 0) {
        fprintf(stderr, "Warning: Failed to open %s\n", DIFF_NODE);
    }

    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);

    // Write PID file
    FILE *pf = fopen(PID_FILE, "w");
    if (pf) {
        fprintf(pf, "%d\n", getpid());
        fclose(pf);
    }

    double last_active_time = get_time_sec();
    float hue = 0.0f;
    float fade = 0.0f;
    int leds_active = 0;

    printf("[ambient-lights-c] Native C ambient daemon started (PID %d)\n", getpid());

    while (running) {
        int c0 = 0, c1 = 0, c2 = 0;
        read_diff(&c0, &c1, &c2);
        double now = get_time_sec();

        // Check if hard muted
        if (access("/tmp/hard_mic_muted", F_OK) == 0) {
            if (leds_active) {
                all_off();
                leds_active = 0;
                fade = 0.0f;
            }
            usleep(250000);
            continue;
        }

        if (c0 >= TOUCH_THRESHOLD || c1 >= TOUCH_THRESHOLD || c2 >= TOUCH_THRESHOLD) {
            last_active_time = now;
            if (leds_active) {
                all_off();
                leds_active = 0;
                fade = 0.0f;
            }
            usleep(40000);
            continue;
        }

        double idle_duration = now - last_active_time;

        if (idle_duration >= IDLE_TIMEOUT) {
            leds_active = 1;
            if (fade < 1.0f) {
                fade += 0.015f;
                if (fade > 1.0f) fade = 1.0f;
            }

            int r1, g1, b1, r2, g2, b2, r3, g3, b3;
            get_color(hue, fade, &r1, &g1, &b1);
            get_color(hue + 50.0f, fade, &r2, &g2, &b2);
            get_color(hue + 100.0f, fade, &r3, &g3, &b3);

            set_ring(0, r1, g1, b1);
            set_ring(1, r2, g2, b2);
            set_ring(2, r3, g3, b3);

            hue = fmodf(hue + 0.45f, 360.0f);
            usleep(20000); // 50 FPS
        } else {
            if (leds_active) {
                all_off();
                leds_active = 0;
                fade = 0.0f;
            }
            usleep(50000);
        }
    }

    all_off();
    for (int z = 0; z < 3; z++) {
        for (int c = 0; c < 3; c++) {
            if (led_fds[z][c] >= 0) close(led_fds[z][c]);
        }
    }
    if (diff_fd >= 0) close(diff_fd);
    unlink(PID_FILE);

    printf("[ambient-lights-c] Exited cleanly.\n");
    return 0;
}
