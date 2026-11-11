/*
 * station-voice-bridge.c
 *
 * Lightweight native C daemon for Yandex Station Lite (yandexmicro).
 * Intercepts recognized voice phrases from local Quasar aliced IPC (127.0.0.1:9875),
 * matches custom commands (e.g. "включи на ноуте ультракилл", "выруби моник"),
 * cancels the default cloud response, triggers actions on the laptop over TCP,
 * and vocalizes the result using Alice's native voice via TVocalizeDirective.
 *
 * Zero external dependencies. Static memory allocation. 0% CPU footprint.
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <signal.h>
#include <time.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>
#include <sys/stat.h>
#include <poll.h>
#include <pthread.h>

#define ALICE_PORT 9875
#define MAX_FRAME_SIZE (512 * 1024)
#define MAX_RULES 64
#define MAX_TEXT_LEN 512
#define DEFAULT_LAPTOP_IP "192.168.1.178"
#define DEFAULT_LAPTOP_PORT 9777
#define DEFAULT_CONF_PATH "/data/opt/etc/voice-triggers.conf"

#define CMD_FIFO_PATH "/tmp/georgy_cmd"
#define STATUS_FILE "/tmp/georgy_status"

static pthread_t g_cmd_thread;
static int g_georgy_mode = 0;

typedef struct {
    char keywords[MAX_TEXT_LEN]; // e.g. "ноут+ютуб"
    char action[64];             // e.g. "youtube"
    char default_tts[MAX_TEXT_LEN];
} TriggerRule;

static TriggerRule g_rules[MAX_RULES];
static int g_rule_count = 0;
static char g_laptop_ip[64] = DEFAULT_LAPTOP_IP;
static int g_laptop_port = DEFAULT_LAPTOP_PORT;
static volatile sig_atomic_t g_running = 1;

static void sig_handler(int sig) {
    (void)sig;
    g_running = 0;
}

/* ================= UTF-8 Russian Lowercasing ================= */

static void utf8_to_lower(char *str) {
    uint8_t *b = (uint8_t *)str;
    size_t i = 0;
    while (b[i]) {
        if (b[i] >= 'A' && b[i] <= 'Z') {
            b[i] += 32;
            i += 1;
        } else if (b[i] == 0xD0 && b[i + 1]) {
            uint8_t c = b[i + 1];
            if (c >= 0x90 && c <= 0x9F) {
                // А-П -> а-п
                b[i + 1] += 0x20;
                i += 2;
            } else if (c >= 0xA0 && c <= 0xAF) {
                // Р-Я -> р-я
                b[i] = 0xD1;
                b[i + 1] -= 0x20;
                i += 2;
            } else if (c == 0x81) {
                // Ё -> ё
                b[i] = 0xD1;
                b[i + 1] = 0x91;
                i += 2;
            } else {
                i += 2;
            }
        } else if (b[i] >= 0xC0) {
            // Other multi-byte UTF-8, skip
            if ((b[i] & 0xE0) == 0xC0) i += 2;
            else if ((b[i] & 0xF0) == 0xE0) i += 3;
            else if ((b[i] & 0xF8) == 0xF0) i += 4;
            else i += 1;
        } else {
            i += 1;
        }
    }
}

/* ================= Config Loader ================= */

static void load_config(const char *path) {
    g_rule_count = 0;
    FILE *f = fopen(path, "r");
    if (!f) {
        printf("[!] Config file not found at %s. Using built-in fallback rules.\n", path);
        // Fallback built-ins
        strncpy(g_rules[0].keywords, "ультракилл", MAX_TEXT_LEN - 1);
        strncpy(g_rules[0].action, "ultrakill", 63);
        strncpy(g_rules[0].default_tts, "Запускаю Ультракилл на ноуте! Приятной игры!", MAX_TEXT_LEN - 1);

        strncpy(g_rules[1].keywords, "ноут+ютуб", MAX_TEXT_LEN - 1);
        strncpy(g_rules[1].action, "youtube", 63);
        strncpy(g_rules[1].default_tts, "Открываю Ютуб на ноуте!", MAX_TEXT_LEN - 1);

        strncpy(g_rules[2].keywords, "выруби+моник", MAX_TEXT_LEN - 1);
        strncpy(g_rules[2].action, "mon_off", 63);
        strncpy(g_rules[2].default_tts, "Вырубила монитор!", MAX_TEXT_LEN - 1);

        g_rule_count = 3;
        return;
    }

    char line[1024];
    while (fgets(line, sizeof(line), f) && g_rule_count < MAX_RULES) {
        char *p = line;
        while (*p == ' ' || *p == '\t') p++;
        if (*p == '#' || *p == '\n' || *p == '\r' || *p == '\0') continue;

        // Strip newline
        char *nl = strpbrk(p, "\r\n");
        if (nl) *nl = '\0';

        // Format: keywords | action | default_tts
        char *sep1 = strchr(p, '|');
        if (!sep1) continue;
        *sep1 = '\0';
        char *sep2 = strchr(sep1 + 1, '|');
        if (!sep2) continue;
        *sep2 = '\0';

        char *kw = p;
        char *act = sep1 + 1;
        char *tts = sep2 + 1;

        // Trim
        while (*kw == ' ') kw++;
        char *end = kw + strlen(kw) - 1;
        while (end > kw && *end == ' ') *end-- = '\0';

        while (*act == ' ') act++;
        end = act + strlen(act) - 1;
        while (end > act && *end == ' ') *end-- = '\0';

        while (*tts == ' ') tts++;
        end = tts + strlen(tts) - 1;
        while (end > tts && *end == ' ') *end-- = '\0';

        if (strlen(kw) == 0 || strlen(act) == 0) continue;

        utf8_to_lower(kw);
        strncpy(g_rules[g_rule_count].keywords, kw, MAX_TEXT_LEN - 1);
        strncpy(g_rules[g_rule_count].action, act, 63);
        strncpy(g_rules[g_rule_count].default_tts, tts, MAX_TEXT_LEN - 1);
        g_rule_count++;
    }
    fclose(f);
    printf("[+] Loaded %d trigger rules from %s\n", g_rule_count, path);
}

/* ================= Keyword Matching ================= */

// Checks if phrase matches "subword1+subword2+subword3" (all subwords must be in phrase)
static bool match_rule(const char *phrase_lower, const char *keywords_spec) {
    char spec_copy[MAX_TEXT_LEN];
    strncpy(spec_copy, keywords_spec, sizeof(spec_copy) - 1);
    spec_copy[sizeof(spec_copy) - 1] = '\0';

    char *saveptr = NULL;
    char *token = strtok_r(spec_copy, "+", &saveptr);
    while (token) {
        while (*token == ' ') token++;
        char *end = token + strlen(token) - 1;
        while (end > token && *end == ' ') *end-- = '\0';

        if (strlen(token) > 0 && !strstr(phrase_lower, token)) {
            return false;
        }
        token = strtok_r(NULL, "+", &saveptr);
    }
    return true;
}

/* ================= Protobuf Helpers ================= */

static void write_varint(uint8_t *buf, size_t *pos, uint64_t val) {
    while (val >= 128) {
        buf[(*pos)++] = (uint8_t)((val & 0x7F) | 0x80);
        val >>= 7;
    }
    buf[(*pos)++] = (uint8_t)val;
}

static void write_integer(uint8_t *buf, size_t *pos, uint64_t field, uint64_t val) {
    write_varint(buf, pos, (field << 3));
    write_varint(buf, pos, val);
}

static void write_bytes(uint8_t *buf, size_t *pos, uint64_t field, const void *data, size_t len) {
    write_varint(buf, pos, (field << 3) | 2);
    write_varint(buf, pos, len);
    if (len > 0 && data) {
        memcpy(buf + *pos, data, len);
        *pos += len;
    }
}

static size_t build_rpc_frame(uint8_t *out, uint64_t field, const uint8_t *payload, size_t payload_len) {
    uint8_t remote[1024];
    size_t remote_len = 0;
    write_bytes(remote, &remote_len, 7, "AliceCapability", 15);
    write_bytes(remote, &remote_len, field, payload, payload_len);

    uint8_t envelope[2048];
    size_t env_len = 0;
    write_bytes(envelope, &env_len, 252, remote, remote_len);
    write_integer(envelope, &env_len, 253, 210);

    uint32_t len32 = (uint32_t)env_len;
    out[0] = (uint8_t)(len32 & 0xFF);
    out[1] = (uint8_t)((len32 >> 8) & 0xFF);
    out[2] = (uint8_t)((len32 >> 16) & 0xFF);
    out[3] = (uint8_t)((len32 >> 24) & 0xFF);
    memcpy(out + 4, envelope, env_len);
    return env_len + 4;
}

static bool send_all(int fd, const void *data, size_t len) {
    size_t sent = 0;
    const uint8_t *p = (const uint8_t *)data;
    while (sent < len) {
        ssize_t n = write(fd, p + sent, len - sent);
        if (n <= 0) return false;
        sent += (size_t)n;
    }
    return true;
}

static bool send_subscribe(int fd) {
    uint8_t sub[64];
    size_t pos = 0;
    write_bytes(sub, &pos, 1, "AliceCapability", 15);

    uint8_t frame[256];
    size_t len = build_rpc_frame(frame, 20, sub, pos);
    return send_all(fd, frame, len);
}

static bool send_cancel(int fd) {
    uint8_t payload[64];
    size_t pos = 0;
    write_integer(payload, &pos, 1, 6); // CANCEL_DIALOG_AND_CLEAR_QUEUE = 6

    uint8_t frame[256];
    size_t len = build_rpc_frame(frame, 8, payload, pos);
    return send_all(fd, frame, len);
}

static bool send_vocalize(int fd, const char *text) {
    uint8_t directive[1024];
    size_t dir_len = 0;
    write_bytes(directive, &dir_len, 1, text, strlen(text));
    write_integer(directive, &dir_len, 2, 1); // Append = 1

    uint8_t payload[1536];
    size_t pay_len = 0;
    write_integer(payload, &pay_len, 1, 18); // START_VOCALIZE = 18
    write_integer(payload, &pay_len, 3, 1);  // events = true
    write_bytes(payload, &pay_len, 13, directive, dir_len);

    uint8_t frame[2048];
    size_t len = build_rpc_frame(frame, 8, payload, pay_len);
    return send_all(fd, frame, len);
}

/* ================= Protobuf Decoding ================= */

static int read_varint(const uint8_t **p, const uint8_t *end, uint64_t *v) {
    uint64_t x = 0;
    for (int shift = 0; *p < end && shift < 64; shift += 7) {
        uint8_t b = *(*p)++;
        x |= (uint64_t)(b & 0x7F) << shift;
        if (!(b & 0x80)) {
            *v = x;
            return 0;
        }
    }
    return -1;
}

static int find_field(const uint8_t *p, const uint8_t *end, uint64_t target_field, int want_bytes,
                      uint64_t *out_val, const uint8_t **out_data) {
    while (p < end) {
        uint64_t tag, x;
        if (read_varint(&p, end, &tag)) return -1;
        uint64_t field_num = tag >> 3;
        int wire = (int)(tag & 7);

        switch (wire) {
            case 0:
                if (read_varint(&p, end, &x)) return -1;
                if (field_num == target_field && !want_bytes) {
                    *out_val = x;
                    return 0;
                }
                break;
            case 1:
                if (end - p < 8) return -1;
                p += 8;
                break;
            case 5:
                if (end - p < 4) return -1;
                p += 4;
                break;
            case 2:
                if (read_varint(&p, end, &x) || x > (uint64_t)(end - p)) return -1;
                if (field_num == target_field && want_bytes) {
                    *out_data = p;
                    *out_val = x;
                    return 0;
                }
                p += x;
                break;
            default:
                return -1;
        }
    }
    return -1;
}

/* ================= Communication with Laptop ================= */

static bool send_raw_to_laptop(const char *command, char *resp_buf, size_t resp_buf_size) {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) return false;

    int flags = fcntl(sock, F_GETFL, 0);
    fcntl(sock, F_SETFL, flags | O_NONBLOCK);

    struct sockaddr_in saddr;
    memset(&saddr, 0, sizeof(saddr));
    saddr.sin_family = AF_INET;
    saddr.sin_port = htons((uint16_t)g_laptop_port);
    inet_pton(AF_INET, g_laptop_ip, &saddr.sin_addr);

    connect(sock, (struct sockaddr *)&saddr, sizeof(saddr));

    struct pollfd pfd;
    pfd.fd = sock;
    pfd.events = POLLOUT;
    if (poll(&pfd, 1, 1500) <= 0) {
        close(sock);
        return false;
    }

    int err = 0;
    socklen_t errlen = sizeof(err);
    if (getsockopt(sock, SOL_SOCKET, SO_ERROR, &err, &errlen) < 0 || err != 0) {
        close(sock);
        return false;
    }

    fcntl(sock, F_SETFL, flags);
    struct timeval tv = {.tv_sec = 2, .tv_usec = 0};
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));

    if (!send_all(sock, command, strlen(command))) {
        close(sock);
        return false;
    }

    if (resp_buf && resp_buf_size > 0) {
        ssize_t n = read(sock, resp_buf, resp_buf_size - 1);
        if (n > 0) {
            resp_buf[n] = '\0';
            char *nl = strpbrk(resp_buf, "\r\n");
            if (nl) *nl = '\0';
        } else {
            resp_buf[0] = '\0';
        }
    }
    close(sock);
    return true;
}

static bool execute_on_laptop(const char *action, char *tts_buf, size_t tts_buf_size) {
    char req[128];
    snprintf(req, sizeof(req), "ACTION %s\n", action);
    char resp[512] = "";
    if (!send_raw_to_laptop(req, resp, sizeof(resp))) return false;

    if (strncmp(resp, "OK ", 3) == 0) {
        char *custom_tts = resp + 3;
        while (*custom_tts == ' ') custom_tts++;
        if (strlen(custom_tts) > 0) {
            strncpy(tts_buf, custom_tts, tts_buf_size - 1);
            tts_buf[tts_buf_size - 1] = '\0';
        }
        return true;
    }
    return false;
}

/* ================= Command Listener (Toggle / On / Off) ================= */

static void *cmd_listener_thread(void *arg) {
    (void)arg;
    unlink(CMD_FIFO_PATH);
    if (mkfifo(CMD_FIFO_PATH, 0666) < 0 && errno != EEXIST) {
        printf("[!] Failed to create %s: %s\n", CMD_FIFO_PATH, strerror(errno));
        return NULL;
    }

    int fd = open(CMD_FIFO_PATH, O_RDWR);
    if (fd < 0) {
        printf("[!] Failed to open %s: %s\n", CMD_FIFO_PATH, strerror(errno));
        return NULL;
    }
    printf("[+] Command listener active at %s\n", CMD_FIFO_PATH);

    // Write initial status
    FILE *sf = fopen(STATUS_FILE, "w");
    if (sf) { fprintf(sf, "%d\n", g_georgy_mode); fclose(sf); }

    char buf[128];
    while (g_running) {
        ssize_t n = read(fd, buf, sizeof(buf) - 1);
        if (n <= 0) {
            usleep(100000);
            continue;
        }
        buf[n] = '\0';
        char *nl = strpbrk(buf, "\r\n");
        if (nl) *nl = '\0';

        char *p = buf;
        while (*p == ' ') p++;

        printf("[*] Received control command: \"%s\"\n", p);

        if (strcmp(p, "toggle") == 0) {
            char resp[128] = "";
            if (!g_georgy_mode) {
                g_georgy_mode = 1;
                printf("[+] GEORGY ACTIVATED via toggle command!\n");
                send_raw_to_laptop("GEORGY_ACTIVATE\n", resp, sizeof(resp));
            } else {
                g_georgy_mode = 0;
                printf("[*] GEORGY DEACTIVATED via toggle command!\n");
                send_raw_to_laptop("GEORGY пока\n", resp, sizeof(resp));
            }
        } else if (strcmp(p, "on") == 0 || strcmp(p, "start") == 0) {
            if (!g_georgy_mode) {
                g_georgy_mode = 1;
                printf("[+] GEORGY ACTIVATED via on command!\n");
                char resp[128] = "";
                send_raw_to_laptop("GEORGY_ACTIVATE\n", resp, sizeof(resp));
            }
        } else if (strcmp(p, "off") == 0 || strcmp(p, "stop") == 0) {
            if (g_georgy_mode) {
                g_georgy_mode = 0;
                printf("[*] GEORGY DEACTIVATED via off command!\n");
                char resp[128] = "";
                send_raw_to_laptop("GEORGY пока\n", resp, sizeof(resp));
            }
        }

        // Update status file
        sf = fopen(STATUS_FILE, "w");
        if (sf) { fprintf(sf, "%d\n", g_georgy_mode); fclose(sf); }
    }

    close(fd);
    unlink(CMD_FIFO_PATH);
    return NULL;
}

/* ================= Frame Processor ================= */

static int g_alice_state = 0;
static bool g_armed = false;
static bool g_handled = false;
static char g_last_req_id[64] = "";

static void process_frame(int alice_fd, const uint8_t *buf, size_t len) {
    uint64_t type = 0, state_len = 0;
    const uint8_t *state_payload = NULL;

    if (find_field(buf, buf + len, 253, 0, &type, NULL) != 0) return;
    if (find_field(buf, buf + len, 252, 1, &state_len, &state_payload) != 0) return;

    if (type == 210) {
        uint64_t capability_len = 0, submsg_len = 0;
        const uint8_t *cap_str = NULL, *submsg = NULL;
        if (find_field(state_payload, state_payload + state_len, 7, 1, &capability_len, &cap_str) == 0 &&
            capability_len == 15 && memcmp(cap_str, "AliceCapability", 15) == 0) {
            if (find_field(state_payload, state_payload + state_len, 18, 1, &submsg_len, &submsg) == 0) {
                uint64_t listener_status = 0, inner_len = 0;
                const uint8_t *inner = NULL;
                find_field(submsg, submsg + submsg_len, 1, 0, &listener_status, NULL);
                if (listener_status == 0 && find_field(submsg, submsg + submsg_len, 2, 1, &inner_len, &inner) == 0) {
                    state_payload = inner;
                    state_len = inner_len;
                    type = 3; // normalized
                }
            }
        }
    }

    if (type != 3) return;

    uint64_t status = 0;
    if (find_field(state_payload, state_payload + state_len, 1, 0, &status, NULL) != 0) {
        status = 0; // 0 = idle
    }

    if (status == 1 && g_alice_state != 1) {
        g_armed = true;
        g_handled = false;
    }
    g_alice_state = (int)status;

    uint64_t text_len = 0;
    const uint8_t *text_data = NULL;
    if (find_field(state_payload, state_payload + state_len, 2, 1, &text_len, &text_data) != 0 || text_len == 0) {
        return;
    }

    if (g_armed && !g_handled && status != 1) {
        g_handled = true;

        uint64_t req_len = 0;
        const uint8_t *req_data = NULL;
        if (find_field(state_payload, state_payload + state_len, 7, 1, &req_len, &req_data) == 0 && req_len > 0) {
            char current_req[64];
            size_t copy_l = req_len < sizeof(current_req) - 1 ? req_len : sizeof(current_req) - 1;
            memcpy(current_req, req_data, copy_l);
            current_req[copy_l] = '\0';
            if (strcmp(current_req, g_last_req_id) == 0) return;
            strncpy(g_last_req_id, current_req, sizeof(g_last_req_id) - 1);
        }

        char phrase[MAX_TEXT_LEN];
        size_t cplen = text_len < sizeof(phrase) - 1 ? text_len : sizeof(phrase) - 1;
        memcpy(phrase, text_data, cplen);
        phrase[cplen] = '\0';

        char phrase_lower[MAX_TEXT_LEN];
        strncpy(phrase_lower, phrase, sizeof(phrase_lower) - 1);
        phrase_lower[sizeof(phrase_lower) - 1] = '\0';
        utf8_to_lower(phrase_lower);

        printf("[*] Heard phrase: \"%s\"\n", phrase);

        // 1. Check Georgy activation or command explicitly mentioning Georgy
        if (strstr(phrase_lower, "георги")) {
            send_cancel(alice_fd);
            char resp[128] = "";
            if (!g_georgy_mode) {
                printf("[+] GEORGY ACTIVATED via voice!\n");
                g_georgy_mode = 1;
                FILE *sf = fopen(STATUS_FILE, "w");
                if (sf) { fprintf(sf, "1\n"); fclose(sf); }

                // If it was just "давай георгия" / "георгий", send greeting
                if (strstr(phrase_lower, "давай") || strstr(phrase_lower, "позови") || strstr(phrase_lower, "включи") || strlen(phrase_lower) <= 24) {
                    send_raw_to_laptop("GEORGY_ACTIVATE\n", resp, sizeof(resp));
                    return;
                }
            }
            // If already active or combined with command:
            printf("[+] GEORGY MODE active, dispatching: \"%s\"\n", phrase);
            char req[MAX_TEXT_LEN + 32];
            snprintf(req, sizeof(req), "GEORGY %s\n", phrase);
            send_raw_to_laptop(req, resp, sizeof(resp));
            if (strstr(resp, "DEACTIVATE")) {
                printf("[*] GEORGY DEACTIVATED, returning to Alice.\n");
                g_georgy_mode = 0;
                FILE *sf = fopen(STATUS_FILE, "w");
                if (sf) { fprintf(sf, "0\n"); fclose(sf); }
            }
            return;
        }

        // 2. If Georgy mode is already active, intercept all phrases
        if (g_georgy_mode) {
            printf("[+] GEORGY MODE active, dispatching: \"%s\"\n", phrase);
            send_cancel(alice_fd);
            char req[MAX_TEXT_LEN + 32];
            snprintf(req, sizeof(req), "GEORGY %s\n", phrase);
            char resp[128] = "";
            send_raw_to_laptop(req, resp, sizeof(resp));
            if (strstr(resp, "DEACTIVATE")) {
                printf("[*] GEORGY DEACTIVATED, returning to Alice.\n");
                g_georgy_mode = 0;
                FILE *sf = fopen(STATUS_FILE, "w");
                if (sf) { fprintf(sf, "0\n"); fclose(sf); }
            }
            return;
        }

        // Check rules
        for (int i = 0; i < g_rule_count; i++) {
            if (match_rule(phrase_lower, g_rules[i].keywords)) {
                printf("[+] TRIGGER MATCH: \"%s\" -> action: %s\n", g_rules[i].keywords, g_rules[i].action);

                // 1. Cancel Alice's native dialog & clear playback queue
                send_cancel(alice_fd);
                printf("[+] Sent CANCEL_DIALOG_AND_CLEAR_QUEUE to Alice\n");

                // 2. Dispatch command to laptop
                char tts_text[MAX_TEXT_LEN];
                strncpy(tts_text, g_rules[i].default_tts, sizeof(tts_text) - 1);
                tts_text[sizeof(tts_text) - 1] = '\0';

                bool ok = execute_on_laptop(g_rules[i].action, tts_text, sizeof(tts_text));
                if (!ok) {
                    printf("[-] Failed to contact laptop at %s:%d\n", g_laptop_ip, g_laptop_port);
                    strncpy(tts_text, "Ноутбук не отвечает в сети.", sizeof(tts_text) - 1);
                } else {
                    printf("[+] Laptop executed action successfully. TTS: \"%s\"\n", tts_text);
                }

                // 3. Vocalize response via Alice's native TTS
                send_vocalize(alice_fd, tts_text);
                printf("[+] Sent TVocalizeDirective to Alice: \"%s\"\n", tts_text);
                break;
            }
        }
    }
}

/* ================= Main Connection Loop ================= */

int main(int argc, char *argv[]) {
    setvbuf(stdout, NULL, _IOLBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);
    if (argc >= 3 && strcmp(argv[1], "say") == 0) {
        int fd = socket(AF_INET, SOCK_STREAM, 0);
        if (fd < 0) return 1;
        struct sockaddr_in addr;
        memset(&addr, 0, sizeof(addr));
        addr.sin_family = AF_INET;
        addr.sin_port = htons(ALICE_PORT);
        addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
            close(fd);
            return 1;
        }
        send_subscribe(fd);
        send_vocalize(fd, argv[2]);
        close(fd);
        return 0;
    }

    const char *conf_path = DEFAULT_CONF_PATH;
    if (argc > 1) {
        for (int i = 1; i < argc; i++) {
            if (strcmp(argv[i], "-c") == 0 && i + 1 < argc) {
                conf_path = argv[++i];
            } else if (strcmp(argv[i], "-l") == 0 && i + 1 < argc) {
                strncpy(g_laptop_ip, argv[++i], sizeof(g_laptop_ip) - 1);
            } else if (strcmp(argv[i], "-p") == 0 && i + 1 < argc) {
                g_laptop_port = atoi(argv[++i]);
            }
        }
    }

    signal(SIGINT, sig_handler);
    signal(SIGTERM, sig_handler);
    signal(SIGPIPE, SIG_IGN);

    printf("=== Station Voice Bridge Daemon starting ===\n");
    printf("[*] Laptop target: %s:%d\n", g_laptop_ip, g_laptop_port);
    load_config(conf_path);

    // Start background control command listener thread (FIFO /tmp/georgy_cmd)
    if (pthread_create(&g_cmd_thread, NULL, cmd_listener_thread, NULL) != 0) {
        fprintf(stderr, "[!] Failed to create command listener thread\n");
    }

    uint8_t *frame_buf = malloc(MAX_FRAME_SIZE);
    if (!frame_buf) {
        fprintf(stderr, "[!] Out of memory\n");
        return 1;
    }

    while (g_running) {
        int fd = socket(AF_INET, SOCK_STREAM, 0);
        if (fd < 0) {
            sleep(2);
            continue;
        }

        struct sockaddr_in addr;
        memset(&addr, 0, sizeof(addr));
        addr.sin_family = AF_INET;
        addr.sin_port = htons(ALICE_PORT);
        addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);

        printf("[*] Connecting to Alice IPC at 127.0.0.1:%d...\n", ALICE_PORT);
        if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
            close(fd);
            sleep(2);
            continue;
        }

        int nodelay = 1;
        setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &nodelay, sizeof(nodelay));

        if (!send_subscribe(fd)) {
            printf("[!] Failed to send subscribe frame\n");
            close(fd);
            sleep(2);
            continue;
        }
        printf("[+] Connected and subscribed to AliceCapability events!\n");

        while (g_running) {
            uint8_t hdr[4];
            size_t got = 0;
            while (got < 4 && g_running) {
                ssize_t r = read(fd, hdr + got, 4 - got);
                if (r <= 0) break;
                got += (size_t)r;
            }
            if (got < 4) break;

            uint32_t frame_len = (uint32_t)hdr[0] |
                                 ((uint32_t)hdr[1] << 8) |
                                 ((uint32_t)hdr[2] << 16) |
                                 ((uint32_t)hdr[3] << 24);

            if (frame_len == 0 || frame_len > MAX_FRAME_SIZE) {
                printf("[!] Invalid frame size: %u\n", frame_len);
                break;
            }

            got = 0;
            while (got < frame_len && g_running) {
                ssize_t r = read(fd, frame_buf + got, frame_len - got);
                if (r <= 0) break;
                got += (size_t)r;
            }
            if (got < frame_len) break;

            process_frame(fd, frame_buf, frame_len);
        }

        close(fd);
        if (g_running) {
            printf("[!] Connection lost. Reconnecting in 2 seconds...\n");
            sleep(2);
        }
    }

    free(frame_buf);
    if (g_cmd_thread) {
        pthread_join(g_cmd_thread, NULL);
    }
    printf("[*] Daemon stopped cleanly.\n");
    return 0;
}
