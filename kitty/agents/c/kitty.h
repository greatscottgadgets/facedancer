/*
* Copyright (C) 2016 Cisco Systems, Inc. and/or its affiliates. All rights reserved.
*
* This file is part of Kitty.
*
* Kitty is free software: you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation, either version 2 of the License, or
* (at your option) any later version.
*
* Kitty is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with Kitty.  If not, see <http://www.gnu.org/licenses/>.
*/

#ifndef KITTY_H
#define KITTY_H

#include <stdio.h>
#include <curl/curl.h>

// Logging macros
#ifndef DLog
#   ifdef KITTY_DEBUG
#       ifndef LOG_PREFIX
#           define LOG_PREFIX      "[kitty]"
#       endif // LOG_PREFIX
#       define DLog( x, ... ) printf(LOG_PREFIX " " x "\n", ##__VA_ARGS__ )
#   else
#       define DLog( x, ... ) do{}while(0)
#   endif // KITTY_DEBUG
#endif // DLog

struct kitty_buff{
    unsigned char * buffer;
    int buffer_len;
};

typedef struct kitty_buff kitty_buff;
typedef struct kitty kitty;

kitty * kitty_init(const char * host, int port);
int kitty_destroy(kitty * p_agent);
int kitty_start(kitty * p_agent);
int kitty_quit(kitty * p_agent);
int kitty_get_mutation( kitty * p_agent, const char * stage, kitty_buff ** pp_mutation);
int kitty_add_session_data( kitty * p_kitty,
                            const char * key,
                            const unsigned char * p_value,
                            size_t value_len);
int kitty_del_session_data(kitty * p_kitty, const char * key);
kitty_buff * kitty_buffer_create(const unsigned char * buffer, int buffer_len);
int kitty_buffer_release(kitty_buff * p_buffer);
#endif // KITTY_H