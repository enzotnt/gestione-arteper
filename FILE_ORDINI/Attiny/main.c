#include <avr/io.h>
#include <util/delay.h>
#include "light_ws2812.h"

#define PIXEL_NUM 9
#define FADE_DELAY 10

struct pixel {
    uint8_t g;
    uint8_t b;
    uint8_t r;
} pixels[PIXEL_NUM];

void delay_ms(uint16_t milliseconds) {
    while (milliseconds--) {
        _delay_ms(1);
    }
}

void initialize_LEDs() {
    uint8_t i;
    for (i = 0; i < PIXEL_NUM; i++) {
        pixels[i].r = 255;
        pixels[i].g = 255;
        pixels[i].b = 255;
    }
    ws2812_setleds((struct cRGB *)pixels, PIXEL_NUM);
}

void set_LED_color(uint8_t led_index, uint8_t r, uint8_t g, uint8_t b) {
    if (led_index < PIXEL_NUM) {
        pixels[led_index].r = r;
        pixels[led_index].g = g;
        pixels[led_index].b = b;
    }
    ws2812_setleds((struct cRGB *)pixels, PIXEL_NUM);
}

void fade_LED_color(uint8_t led_index, uint8_t target_r, uint8_t target_g) {
    uint8_t current_r = pixels[led_index].r;
    uint8_t current_g = pixels[led_index].g;

    while (current_r != target_r || current_g != target_g) {
        if (current_r > target_r) current_r--;
        else if (current_r < target_r) current_r++;

        if (current_g > target_g) current_g--;
        else if (current_g < target_g) current_g++;

        set_LED_color(led_index, current_r, current_g, pixels[led_index].b);
        delay_ms(FADE_DELAY);
    }
}

// ...

// ...

// ...

// ...

// ...

// ...

void move_light_effect() {
    while (1) {
        // Dissolvenza in discesa
        for (int i = 255; i >= 0; i -= 85) {
            fade_LED_color(4, i, 255);   // Modifica qui: arancio
            fade_LED_color(3, i, 255);   // Modifica qui: arancio
            fade_LED_color(5, i, 255);   // Modifica qui: arancio
            fade_LED_color(2, i, 255);   // Modifica qui: arancio
            fade_LED_color(6, i, 255);   // Modifica qui: arancio
            fade_LED_color(1, i, 255);   // Modifica qui: arancio
            fade_LED_color(7, i, 255);   // Modifica qui: arancio
            fade_LED_color(0, i, 255);   // Modifica qui: arancio
            fade_LED_color(8, i, 255);   // Modifica qui: arancio
        }

        delay_ms(10000);

        // Dissolvenza in salita
        for (int i = 0; i <= 255; i += 85) {
            fade_LED_color(4, i, 255);   // Modifica qui: arancio
            fade_LED_color(3, i, 255);   // Modifica qui: arancio
            fade_LED_color(5, i, 255);   // Modifica qui: arancio
            fade_LED_color(2, i, 255);   // Modifica qui: arancio
            fade_LED_color(6, i, 255);   // Modifica qui: arancio
            fade_LED_color(1, i, 255);   // Modifica qui: arancio
            fade_LED_color(7, i, 255);   // Modifica qui: arancio
            fade_LED_color(0, i, 255);   // Modifica qui: arancio
            fade_LED_color(8, i, 255);   // Modifica qui: arancio
        }
    }
}

// ...



// ...





// ...


// ...


// ...


// ...


int main(void) {
    initialize_LEDs();
    move_light_effect();
}
