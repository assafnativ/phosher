
#include "dct4Coder.hpp"
#include <stdint.h>

#ifdef WIN32
BOOL WINAPI DllMain(
                __in  HINSTANCE hinstDLL,
                __in  DWORD fdwReason,
                __in  LPVOID lpvReserved )
{
    return TRUE;
}
#endif

#include "words_perm_table.h"
#include "invers_words_perm_table.h"

static const uint32_t TABLE_SIZE = 25;
static const uint32_t XOR_TABLE_SIZE = 24;

static const uint32_t TABLE_MASKS[TABLE_SIZE] = {
    0x000140, 0x000220, 0x000480, 0x000600, 
    0x000810, 0x000840, 0x000900, 0x001020, 
    0x001080, 0x001100, 0x002020, 0x002080, 
    0x004010, 0x004040, 0x008008, 0x009000, 
    0x00a000, 0x010010, 0x010040, 0x010400, 
    0x020200, 0x040040, 0x044000, 0x080100, 
    0x800000 };

static const uint16_t TABLE[TABLE_SIZE] = {
    0x1000, 0x52a1, 0x1221, 0xb928, 0x5221, 
    0x1220, 0x2008, 0x1221, 0x0908, 0x52a1, 
    0x0100, 0xfbbd, 0xa91a, 0xa908, 0x2908, 
    0x1000, 0xbd3a, 0xad1a, 0x5221, 0x0908, 
    0x53a5, 0xa91a, 0x1b20, 0xa918, 0xb908 };

static const uint16_t XOR_TABLE[XOR_TABLE_SIZE] = {
    0x0fae, 0x3e7f, 0xc99f, 0xd6f7, 0xa71b, 
    0x14c4, 0x52a5, 0xcbb1, 0x4285, 0xefdf, 
    0xdff7, 0x5080, 0xee9f, 0x0000, 0x8432, 
    0x5221, 0x4084, 0xa91a, 0x56e7, 0xb93a, 
    0x5b21, 0xa818, 0x0000, 0xefdf };

inline uint16_t cryptoInternal(uint16_t word, uint16_t addr)
{
    uint32_t i;
    for (i = 0; i < TABLE_SIZE; ++i) {
        if( (addr & TABLE_MASKS[i]) == TABLE_MASKS[i] ) {
            word ^= TABLE[i];
        }
    }
    uint32_t bit = 1;
    for (i = 0; i < XOR_TABLE_SIZE; ++i) {
        bit <<= 1;
        if (addr & bit) {
            word ^= XOR_TABLE[i];
        }
    }
    return word;
}

DCT4CODER_API int decryptChunk( uint8_t * data, uint32_t length, uint32_t base )
{
    uint32_t pos;
    uint32_t addr;
    uint16_t  currentWord;

    for (pos = 0; pos < length; pos += 2) {
        addr = base + pos;

        currentWord  = data[pos] << 8;
        currentWord |= data[pos ^ 1];

        currentWord = cryptoInternal( currentWord, addr );

        currentWord = WORDS_PERM_TABLE[currentWord];
        data[pos] = currentWord >> 8;
        data[pos ^ 1] = (uint8_t)currentWord;
    }

    return 0;
}

DCT4CODER_API int encryptChunk( uint8_t * data, uint32_t length, uint32_t base )
{
    uint32_t pos;
    uint32_t addr;
    uint16_t currentWord;

    for (pos = 0; pos < length; pos += 2) {
        addr = base + pos;
        currentWord  = data[pos] << 8;
        currentWord |= data[pos ^ 1];

        currentWord ^= 0x8a1b;
        currentWord = INVERS_WORDS_PERM_TABLE[currentWord];
        currentWord = cryptoInternal( currentWord, addr );

        data[pos] = currentWord >> 8;
        data[pos ^ 1] = (UCHAR)currentWord;
    }

    return 0;
}

DCT4CODER_API int xorStrings( uint8_t * data, uint32_t length, const uint8_t * xorStr, uint32_t xorStrLength )
{
    uint8_t * end = data + length;
    uint32_t xorPos = 0;
    while (data != end) {
        *data ^= xorStr[xorPos % xorStrLength];
        ++data;
        ++xorPos;
    }
    return 0;
}
