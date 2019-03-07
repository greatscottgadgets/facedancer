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

#include <string.h>
#include <assert.h>
#include "kitty.h"
#include "json-c/json.h"

struct kitty_session_data {
    struct kitty_session_data * p_next;
    char * key;
    kitty_buff * value;
};
typedef struct kitty_session_data kitty_session_data;

struct kitty {
    char * host;
    int port;
    char * url;
    CURL * hcurl;
    kitty_session_data * p_data;
};


static void buff2hex(const unsigned char * p_data, size_t data_len, char * p_hex);
static void hex2buff(const char * hex, unsigned char *bin);
static json_object * _data_to_json_object(kitty * p_agent);
static json_object * json_object_string_value(const unsigned char * p_data, size_t data_len);
static size_t curl_write_to_memory(void *contents, size_t size, size_t nmemb, void *userp);

static json_object * build_request(kitty * p_agent, const char * method, json_object * j_params)
{
    json_object * j_msg;
    int id = 0;
    j_msg = json_object_new_object();
    json_object_object_add(j_msg, "jsonrpc", json_object_new_string("2.0"));
    json_object_object_add(j_msg, "id", json_object_new_int(id));
    json_object_object_add(j_msg, "method", json_object_new_string(method));
    if(!j_params)
    {
        j_params = json_object_new_object();
    }
    json_object_object_add(j_msg, "params", j_params);
    return j_msg;
}

static int rpc_call(kitty * p_agent, const char * method_name, json_object * j_params, json_object ** pj_response)
{
    json_object * j_request;
    if(pj_response)
    {
        *pj_response = NULL;
    }
    j_request = build_request(p_agent, method_name, j_params);
    kitty_buff response_buff = { 0 };
    curl_easy_setopt(p_agent->hcurl, CURLOPT_POSTFIELDS, json_object_to_json_string(j_request));
    curl_easy_setopt(p_agent->hcurl, CURLOPT_WRITEDATA, &response_buff);
    curl_easy_perform(p_agent->hcurl);
    json_object_put(j_request);
    if(response_buff.buffer)
    {
        DLog("Response buffer(%d): %s", response_buff.buffer_len, response_buff.buffer);
        if(pj_response)
        {
            *pj_response = json_tokener_parse((char *)response_buff.buffer);
            DLog("Response object: %p", *pj_response);
        }
        free(response_buff.buffer);
        return 0;
    }
    return 1;
}


/************************************************************
                        Utils
************************************************************/
static void buff2hex(const unsigned char * p_data, size_t data_len, char * p_hex)
{
    int i = 0;
    const char * digits = "0123456789abcdef";
    for (; i < data_len; ++i)
    {
        unsigned char c = p_data[i];
        *p_hex++ = digits[(c >> 4) & 0xf];
        *p_hex++ = digits[c & 0xf];
    }
    *p_hex = '\x00';
}

static unsigned char h2bnibble(char hex)
{
    if(hex >= '0' && hex <= '9')
        return hex - '0';
    else if(hex >= 'a' && hex <= 'f')
        return hex - 'a' + 10;
    else if(hex >= 'A' && hex <= 'F')
        return hex - 'A' + 10;
    DLog("character (%c) is not hex!!", hex);
    assert(0);
    //return -1;
}

static void hex2buff(const char * hex, unsigned char *bin)
{
    assert(strlen(hex) % 2 == 0);
    while(*hex)
    {
        *bin = h2bnibble(*hex++) << 4;
        *bin++ |= h2bnibble(*hex++);
    }
}

// create a json string with hex encoded string representing p_data
static json_object * json_object_string_value(const unsigned char * p_data, size_t data_len)
{
    char * hex_buff;
    json_object * j_val;
    hex_buff = malloc(data_len * 2 + 1);
    assert(hex_buff);
    buff2hex(p_data, data_len, hex_buff);
    j_val = json_object_new_string(hex_buff);
    free(hex_buff);
    return j_val;
}

// create a json object of all session data entries
static json_object * _data_to_json_object(kitty * p_agent)
{
    json_object * j_params;
    j_params = json_object_new_object();
    kitty_session_data * params = p_agent->p_data;
    while(params && params->key)
    {
        json_object * j_val;
        j_val = json_object_string_value(params->value->buffer, params->value->buffer_len);
        DLog("session_data:key: %s", params->key);
        DLog("session_data:hex value: %s", json_object_get_string(j_val));
        json_object_object_add(j_params, params->key, j_val);
        params = params->p_next;
    }
    return j_params;
}

// CURL callback
static size_t curl_write_to_memory(void *contents, size_t size, size_t nmemb, void *userp)
{
  size_t realsize = size * nmemb;
  kitty_buff *p_buff = (kitty_buff *)userp;
 
  p_buff->buffer = realloc(p_buff->buffer, p_buff->buffer_len + realsize + 1);
  if(p_buff->buffer == NULL) {
    /* out of memory! */ 
    DLog("not enough memory (realloc returned NULL)");
    return 0;
  }
 
  memcpy(&(p_buff->buffer[p_buff->buffer_len]), contents, realsize);
  p_buff->buffer_len += realsize;
  p_buff->buffer[p_buff->buffer_len] = 0;
 
  return realsize;
}


/************************************************************
*************************************************************
                        Kitty Agent API
*************************************************************
************************************************************/

kitty * kitty_init(const char * host, int port)
{
    kitty * pk;
    int url_len;
    pk = malloc(sizeof(kitty));
    assert(pk);
    memset(pk, 0, sizeof(kitty));
    /* member init */
    pk->host = strdup(host);
    assert(pk->host);
    pk->port = port;
    pk->url = malloc(1);
    assert(pk->url);
    url_len = snprintf(pk->url, 1, "http://%s:%d", pk->host, pk->port);
    pk->url = realloc(pk->url, url_len + 1);
    assert(pk->url);
    snprintf(pk->url, url_len + 1, "http://%s:%d", pk->host, pk->port);
    /* curl init */
    curl_global_init(CURL_GLOBAL_DEFAULT);
    pk->hcurl = curl_easy_init();
    curl_easy_setopt(pk->hcurl, CURLOPT_URL, pk->url);
    curl_easy_setopt(pk->hcurl, CURLOPT_WRITEFUNCTION, curl_write_to_memory);
    return pk;
}

int kitty_destroy(kitty * p_agent)
{
    if(p_agent){
        while(p_agent->p_data)
        {
            kitty_del_session_data(p_agent, p_agent->p_data->key);
        }
        free(p_agent->url);
        free(p_agent->host);
        curl_easy_cleanup(p_agent->hcurl);
        curl_global_cleanup();
    }
    free(p_agent);
    return 0;
}

/************************************************************
                        RPC API
************************************************************/
int kitty_start(kitty * p_agent)
{
    return rpc_call(p_agent, "start", NULL, NULL);
}

int kitty_quit(kitty * p_agent)
{
    return rpc_call(p_agent, "quit", NULL, NULL);
}

int kitty_get_mutation(kitty * p_agent, const char * stage, kitty_buff ** pp_mutation)
{
    json_object * j_stage, * j_data, * j_params;
    json_object * j_response;
    int res;
    *pp_mutation = NULL;
    j_data = _data_to_json_object(p_agent);
    j_stage = json_object_string_value((const unsigned char *)stage, strlen(stage));
    j_params = json_object_new_object();
    json_object_object_add(j_params, "stage", j_stage);
    json_object_object_add(j_params, "data", j_data);
    res = rpc_call(p_agent, "get_mutation", j_params, &j_response);

    if(!res)
    {
        json_object * j_result;
        if(json_object_object_get_ex(j_response, "result", &j_result) &&
            json_object_is_type(j_result, json_type_string))
        {
            const char * hex_res;
            int non_hex_len;
            kitty_buff * result;
            hex_res = json_object_get_string(j_result);
            non_hex_len = strlen(hex_res) / 2 + 1;
            result = malloc(sizeof(kitty_buff));
            assert(result);
            result->buffer = malloc(non_hex_len);
            assert(result->buffer);
            result->buffer_len = non_hex_len;
            hex2buff(hex_res, result->buffer);
            *pp_mutation = result;
            json_object_put(j_response);
            return 1;
        }
    }
    return 0;
}

/************************************************************
                        Session Data
************************************************************/
int kitty_add_session_data( kitty * p_agent,
                            const char * key,
                            const unsigned char * p_value,
                            size_t value_len)
{
    kitty_session_data ** p_next, * new_data;
    kitty_del_session_data(p_agent, key);
    // move to end of list
    p_next = &p_agent->p_data;
    while(*p_next)
    {
        p_next = &(*p_next)->p_next;
    }
    new_data = malloc(sizeof(kitty_session_data));
    assert(new_data);
    new_data->p_next = NULL;
    new_data->key = strdup(key);
    assert(new_data->key);
    new_data->value = kitty_buffer_create(p_value, value_len);
    *p_next = new_data;
    return 0;
}

int kitty_del_session_data(kitty * p_agent, const char * key)
{
    kitty_session_data ** pp_next;
    char * local_key = strdup(key);
    assert(local_key);
    pp_next = &p_agent->p_data;
    while(*pp_next)
    {
        kitty_session_data * current = *pp_next;
        if (strcmp(current->key, local_key) == 0)
        {
            *pp_next = current->p_next;
            kitty_buffer_release(current->value);
            free(current->key);
            free(current);
        }
        else
        {
            pp_next = &current->p_next;
        }
    }
    free(local_key);
    return 0;
}

/************************************************************
                        Buffers
************************************************************/
kitty_buff * kitty_buffer_create(const unsigned char * buffer, int buffer_len)
{
    kitty_buff * new_buff;
    new_buff = malloc(sizeof(kitty_buff));
    assert(new_buff);
    new_buff->buffer = malloc(buffer_len);
    assert(new_buff->buffer);
    memcpy(new_buff->buffer, buffer, buffer_len);
    new_buff->buffer_len = buffer_len;
    return new_buff;
}

int kitty_buffer_release(kitty_buff * p_buffer)
{
    if(p_buffer)
    {
        free(p_buffer->buffer);    
    }
    free(p_buffer);
    return 0;
}






