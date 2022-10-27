#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>
#include <signal.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
#else
#include <sys/ioctl.h>
#endif

#include "cat.h"


#define CSI "\33["
#define CUR_HIDE "?25l"
#define CUR_SHOW "?25h"
#define CLEAR "2J"
#define RESET "0m"
#define FRAME_MS 20


int get_terminal_size(int *w, int *h) {
    int new_w, new_h;

    #ifdef _WIN32

    CONSOLE_SCREEN_BUFFER_INFO csbi;
    GetConsoleScreenBufferInfo(GetStdHandle(STD_OUTPUT_HANDLE), &csbi);
    new_w = csbi.srWindow.Right - csbi.srWindow.Left + 1;
    new_h = csbi.srWindow.Bottom - csbi.srWindow.Top + 1;

    #else

    struct winsize win_s;
    ioctl(STDOUT_FILENO, TIOCGWINSZ, &win_s);
    new_w = win_s.ws_col;
    new_h = win_s.ws_row;

    #endif

    int ret = new_w != *w || new_h != *h;
    *w = new_w;
    *h = new_h;
    return ret;
}


void write_ansi_number(char *to, int n) {
    for (int i = 2; i >= 0; i--) {
        *(to + i) = '0' + (n % 10);
        n /= 10;
    }
}


void set_offsets(int tw, int th) {
    int dw = (tw - frame_w) / 2 % 1000;
    if (dw < 0) dw = 0;

    int dh = (th - frame_h) / 2 % 1000;
    if (dh < 0) dh = 0;

    /*

    Frame prefix scheme ( ~[ represents CSI ):
    ~[38;5;000m (11 chars)
           ^
           8
           set_fg

    Row prefix scheme ( ~[ represents CSI ):
    ~[000;000H (10 chars)
      ^   ^
      2   6
      cur_pos

    */

    for (int i = 0; i < frame_count; i++) {
        int f_start = i * frame_len + 11;

        for (int j = 0; j < frame_h; j++) {
            int row_start = f_start + j * (frame_w + 10);

            // Cursor position sequence is 1-based
            write_ansi_number(frames + row_start + 2, dh + j + 1);
            write_ansi_number(frames + row_start + 6, dw + 1);
        }
    }
}


void ansi(char *s) {
    printf("%s%s", CSI, s);
}


void handle_sigint() {
    ansi(RESET);
    ansi(CUR_SHOW);
    exit(0);
}


int main() {
    #ifdef _WIN32
    {
        // Enable ANSI support in windows console
        HANDLE handle = GetStdHandle(STD_OUTPUT_HANDLE);
        DWORD mode = 0;
        GetConsoleMode(handle, &mode);
        SetConsoleMode(handle, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);
    }
    #endif

    signal(SIGINT, handle_sigint);

    int tw = -1, th = -1;
    int dw = 0, dh = 0;
    while (1) {
        if (get_terminal_size(&tw, &th))
        {
            ansi(CLEAR);
            ansi(CUR_HIDE);
            set_offsets(tw, th);
        }

        for (int i = 0; i < frame_count; i++)
        {
            time_t t1 = time(NULL);
            fwrite(frames + i * frame_len, frame_len, 1, stdout);
            time_t t2 = time(NULL);
            usleep((FRAME_MS - (t2 - t1)) * 1000);
        }
    }
    return 0;
}