/*
 * Copyright (C) 2021 Freie Universität Berlin
 *
 * This file is subject to the terms and conditions of the GNU Lesser
 * General Public License v2.1. See the file LICENSE in the top level
 * directory for more details.
 */

/**
 * @{
 *
 * @file
 * @brief
 *
 * @author  Martine Lenders <m.lenders@fu-berlin.de>
 */
#ifndef APP_H
#define APP_H

#include "mutex.h"

#ifdef __cplusplus
extern "C" {
#endif

extern mutex_t app_output_mutex;

#define APP_LOG(...) \
    mutex_lock(&app_output_mutex); \
    printf(__VA_ARGS__); \
    mutex_unlock(&app_output_mutex)

#ifdef __cplusplus
}
#endif

#endif /* APP_H */
/** @} */
