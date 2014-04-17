#pragma once

#ifdef WIN32
#include <Windows.h>

#ifdef DCT4CODER_EXPORTS
#define DCT4CODER_API __declspec(dllexport)
#else
#define DCT4CODER_API __declspec(dllimport)
#endif
#endif

#include <stdint.h>

extern "C" {

DCT4CODER_API int decryptChunk( uint8_t * data, uint32_t length, uint32_t base );
DCT4CODER_API int encryptChunk( uint8_t * data, uint32_t length, uint32_t base );
DCT4CODER_API int xorStrings( uint8_t * data, uint32_t length, const uint8_t * xorStr, uint32_t xorStrLength );
}