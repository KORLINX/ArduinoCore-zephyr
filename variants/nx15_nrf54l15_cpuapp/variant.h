/*
 * Copyright (c) 2026 KORLINX
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#pragma once

// Header pins, LEDs, button and I2C have the same Arduino numbers as on the
// NX40; see digital-pin-gpios in the overlay for the full map

// LEDs, active high
#define LED_RED   11 /* P1.09 */
#define LED_BLUE  8  /* P0.04 */
#define LED_GREEN 19 /* P2.03 */
#define LED_RUN   14 /* P2.01 */
#define LED_STATE_ON 1

#define PIN_BUTTON1 7 /* P1.10, active low */

// Serial (uart20, on-board USB-UART) and Wire (bit-banged I2C) pins
#define PIN_SERIAL_RX 21 /* P1.12 */
#define PIN_SERIAL_TX 22 /* P1.13 */
#define SDA 6  /* P2.02 */
#define SCL 23 /* P1.15 */

// On-board parts
#define PIN_VBAT       31 /* P1.14, AIN7 (A5) */
#define PIN_CHG_STATUS 13 /* P2.00, low while charging */
#define PIN_CHG_HICHG  16 /* P2.07 */
#define PIN_CHG_CE     15 /* P2.06 */
#define PIN_6D_CS      17 /* P2.05, held high by the board so the IMU stays in I2C mode */
#define PIN_6D_INT1    12 /* P2.04 */

#define ARDUINO_NX15_NRF54L15
