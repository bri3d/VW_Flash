/***************************************************************************
*          Lempel, Ziv, Storer, and Szymanski Encoding and Decoding
*
*   File    : lzss.c
*   Purpose : Use lzss coding (Storer and Szymanski's modified lz77) to
*             compress/decompress files.
*   Author  : Michael Dipperstein
*   Date    : November 24, 2003
*
****************************************************************************
*   UPDATES
*
*   Date        Change
*   12/10/03    Changed handling of sliding window to better match standard
*               algorithm description.
*   12/11/03    Remebered to copy encoded characters to the sliding window
*               even when there are no more characters in the input stream.
*
****************************************************************************
*
* LZSS: An ANSI C LZss Encoding/Decoding Routine
* Copyright (C) 2003 by Michael Dipperstein (mdipper@cs.ucsb.edu)
*
* This library is free software; you can redistribute it and/or
* modify it under the terms of the GNU Lesser General Public
* License as published by the Free Software Foundation; either
* version 2.1 of the License, or (at your option) any later version.
*
* This library is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
* Lesser General Public License for more details.
*
* You should have received a copy of the GNU Lesser General Public
* License along with this library; if not, write to the Free Software
* Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
*
***************************************************************************/

/***************************************************************************
*                             INCLUDED FILES
***************************************************************************/
#include <stdio.h>
/* For setmode */
#include <fcntl.h>
#include <stdlib.h>
#include "getopt.h"

#ifdef _WIN32
	/* For _O_BINARY */
	#include <io.h>
#endif



/***************************************************************************
*                            TYPE DEFINITIONS
***************************************************************************/
/* unpacked encoded offset and length, gets packed into 12 bits and 4 bits*/
typedef struct encoded_string_t
{
    int offset;     /* offset to start of longest match */
    int length;     /* length of longest match */
} encoded_string_t;

typedef enum
{
    ENCODE,
    DECODE
} MODES;

/***************************************************************************
*                                CONSTANTS
***************************************************************************/
#define FALSE   0
#define TRUE    1

#define WINDOW_SIZE     1023   /* size of sliding window (10 bits) */

/* maximum match length not encoded and encoded (6 bits) */
#define MAX_UNCODED     2
#define MAX_CODED       (61 + MAX_UNCODED + 1)

/***************************************************************************
*                            GLOBAL VARIABLES
***************************************************************************/
/* cyclic buffer sliding window of already read characters */
unsigned char slidingWindow[WINDOW_SIZE];
unsigned char uncodedLookahead[MAX_CODED];

/***************************************************************************
*                               PROTOTYPES
***************************************************************************/
void EncodeLZSS(FILE *inFile, FILE *outFile);   /* encoding routine */
void DecodeLZSS(FILE *inFile, FILE *outFile);   /* decoding routine */

/***************************************************************************
*                                FUNCTIONS
***************************************************************************/

/****************************************************************************
*   Function   : main
*   Description: This is the main function for this program, it validates
*                the command line input and, if valid, it will either
*                encode a file using the LZss algorithm or decode a
*                file encoded with the LZss algorithm.
*   Parameters : argc - number of parameters
*                argv - parameter list
*   Effects    : Encodes/Decodes input file
*   Returned   : EXIT_SUCCESS for success, otherwise EXIT_FAILURE.
****************************************************************************/
int main(int argc, char *argv[])
{
    int opt;
    FILE *inFile, *outFile;  /* input & output files */
    MODES mode;

    /* initialize data */
    inFile = NULL;
    outFile = NULL;
    mode = ENCODE;

    /* parse command line */
    while ((opt = getopt(argc, argv, "cdtnsi:o:h?")) != -1)
    {
        switch(opt)
        {
            case 'c':       /* compression mode */
                mode = ENCODE;
                break;

            case 'd':       /* decompression mode */
                mode = DECODE;
                break;

            case 'i':       /* input file name */
                if (inFile != NULL)
                {
                    fprintf(stderr, "Multiple input files not allowed.\n");
                    fclose(inFile);

                    if (outFile != NULL)
                    {
                        fclose(outFile);
                    }

                    exit(EXIT_FAILURE);
                }
                else if ((inFile = fopen(optarg, "rb")) == NULL)
                {
                    perror("Opening inFile");

                    if (outFile != NULL)
                    {
                        fclose(outFile);
                    }

                    exit(EXIT_FAILURE);
                }
                break;

            case 'o':       /* output file name */
                if (outFile != NULL)
                {
                    fprintf(stderr, "Multiple output files not allowed.\n");
                    fclose(outFile);

                    if (inFile != NULL)
                    {
                        fclose(inFile);
                    }

                    exit(EXIT_FAILURE);
                }
                else if ((outFile = fopen(optarg, "wb")) == NULL)
                {
                    perror("Opening outFile");

                    if (outFile != NULL)
                    {
                        fclose(inFile);
                    }

                    exit(EXIT_FAILURE);
                }
                break;
            
            case 's':
		if _WIN32{
                	_setmode( _fileno( stdin ), _O_BINARY );
                	_setmode( _fileno( stdout ), _O_BINARY );
		}
                inFile = stdin;
                outFile = stdout;
                break;

            case 'h':
            case '?':
                printf("Usage: lzss <options>\n\n");
                printf("options:\n");
                printf("  -c : Encode input file to output file.\n");
                printf("  -d : Decode input file to output file.\n");
                printf("  -i <filename> : Name of input file.\n");
                printf("  -o <filename> : Name of output file.\n");
                printf("  -s : Use STDIN/STDOUT.\n");
                printf("  -h | ?  : Print out command line options.\n\n");
                printf("Default: lzss -c\n");
                return(EXIT_SUCCESS);
        }
    }

    /* validate command line */
    if (inFile == NULL)
    {
        fprintf(stderr, "Input file must be provided\n");
        fprintf(stderr, "Enter \"lzss -?\" for help.\n");

        if (outFile != NULL)
        {
            fclose(outFile);
        }

        exit (EXIT_FAILURE);
    }
    else if (outFile == NULL)
    {
        fprintf(stderr, "Output file must be provided\n");
        fprintf(stderr, "Enter \"lzss -?\" for help.\n");

        if (inFile != NULL)
        {
            fclose(inFile);
        }

        exit (EXIT_FAILURE);
    }

    /* we have valid parameters encode or decode */
    if (mode == ENCODE)
    {
        EncodeLZSS(inFile, outFile);
    }
    else
    {
        DecodeLZSS(inFile, outFile);
    }

    fclose(inFile);
    fclose(outFile);
    return EXIT_SUCCESS;
}

/****************************************************************************
*   Function   : FindMatch
*   Description: This function will search through the slidingWindow
*                dictionary for the longest sequence matching the MAX_CODED
*                long string stored in uncodedLookahed.
*   Parameters : windowHead - head of sliding window
*                uncodedHead - head of uncoded lookahead buffer
*   Effects    : NONE
*   Returned   : The sliding window index where the match starts and the
*                length of the match.  If there is no match a length of
*                zero will be returned.
****************************************************************************/
encoded_string_t FindMatch(int windowHead, int uncodedHead, int uncodedTail)
{
    encoded_string_t matchData;
    int i, j, k;

    matchData.length = 0;
    i = 0;
    j = 0;
    k = 0;

    for (i = 0; i < WINDOW_SIZE; i++)
    {
        for (j = 0; j < MAX_CODED; j++)
        {
            if (j == uncodedTail)
            { 
               break;
            }
            if ((i + j) == WINDOW_SIZE)
            { 
               break;
            }
            if (slidingWindow[(windowHead + i + j) % WINDOW_SIZE] != uncodedLookahead[(uncodedHead + j) % MAX_CODED])
            {
                break;
	    }
            k = j + 1;
            if (k >= matchData.length)
            { 
                matchData.length = k;
                matchData.offset = i;
            }
        }
    }
    return matchData;
}

/****************************************************************************
*   Function   : EncodeLZSS
*   Description: This function will read an input file and write an output
*                file encoded using a slight modification to the LZss
*                algorithm.  I'm not sure who to credit with the slight
*                modification to LZss, but the modification is to group the
*                coded/not coded flag into bytes.  By grouping the flags,
*                the need to be able to write anything other than a byte
*                may be avoided as longs as strings encode as a whole byte
*                multiple.  This algorithm encodes strings as 16 bits (a 12
*                bit offset + a 4 bit length).
*   Parameters : inFile - file to encode
*                outFile - file to write encoded output
*   Effects    : inFile is encoded and written to outFile
*   Returned   : NONE
****************************************************************************/
void EncodeLZSS(FILE *inFile, FILE *outFile)
{
    /* 8 code flags and encoded strings */
    unsigned char flags, flagPos, encodedData[16];
    int nextEncoded;                /* index into encodedData */
    encoded_string_t matchData;
    int i, c;
    int len;                        /* length of string */
    int windowHead, uncodedHead;    /* head of sliding window and lookahead */
    long compressedSize;            /* size of the compressed output file */

    flags = 0;
    flagPos = 0x80;
    nextEncoded = 0;
    windowHead = 0;
    uncodedHead = 0;
    compressedSize = 0;

    /************************************************************************
    * Fill the sliding window buffer with some known vales.  DecodeLZSS must
    * use the same values.  If common characters are used, there's an
    * increased chance of matching to the earlier strings.
    ************************************************************************/
    for (i = 0; i < WINDOW_SIZE; i++)
    {
        slidingWindow[i] = 0x11;
    }

    /************************************************************************
    * Copy MAX_CODED bytes from the input file into the uncoded lookahead
    * buffer.
    ************************************************************************/
    for (len = 0; len < MAX_CODED && (c = getc(inFile)) != EOF; len++)
    {
        uncodedLookahead[len] = c;
    }

    if (len == 0)
    {
        return;  /* inFile was empty */
    }

    /* Look for matching string in sliding window */
    matchData = FindMatch(windowHead, uncodedHead, len);

    /* now encoded the rest of the file until an EOF is read */
    while (len > 0)
    {
        if (matchData.length > 0x3F)
        {
            /* garbage beyond last data happened to extend match length */
            matchData.length = 0x3F;
        }

        if (matchData.length <= MAX_UNCODED)
        {
            /* not long enough match.  write uncoded byte */
            matchData.length = 1;   /* set to 1 for 1 byte uncoded */
            encodedData[nextEncoded++] = uncodedLookahead[uncodedHead];
        }
        else
        {
            /* match length > MAX_UNCODED.  Encode as offset and length. */
            encodedData[nextEncoded++] =
                (unsigned char)(((WINDOW_SIZE - matchData.offset) >> 8) | 
                ((matchData.length) << 2));

            encodedData[nextEncoded++] =
                (unsigned char)((WINDOW_SIZE - matchData.offset) & 0xFF);
            flags |= flagPos;       /* mark with encoded byte flag */
        }

        if (flagPos == 0x01)
        {
            /* we have 8 code flags, write out flags and code buffer */
            putc(flags, outFile);
	    compressedSize++;

            for (i = 0; i < nextEncoded; i++)
            {
                /* send at most 8 units of code together */
                putc(encodedData[i], outFile);
	        compressedSize++;
            }

            /* reset encoded data buffer */
            flags = 0;
            flagPos = 0x80;
            nextEncoded = 0;
        }
        else
        {
            /* we don't have 8 code flags yet, use next bit for next flag */
            flagPos >>= 1;
        }

        /********************************************************************
        * Replace the matchData.length worth of bytes we've matched in the
        * sliding window with new bytes from the input file.
        ********************************************************************/
        i = 0;
        while ((i < matchData.length) && ((c = getc(inFile)) != EOF))
        {
            /* add old byte into sliding window and new into lookahead */
            slidingWindow[windowHead] = uncodedLookahead[uncodedHead];
            uncodedLookahead[uncodedHead] = c;
            windowHead = (windowHead + 1) % WINDOW_SIZE;
            uncodedHead = (uncodedHead + 1) % MAX_CODED;
            i++;
        }

        /* handle case where we hit EOF before filling lookahead */
        while (i < matchData.length)
        {
            slidingWindow[windowHead] = uncodedLookahead[uncodedHead];
            /* nothing to add to lookahead here */
            windowHead = (windowHead + 1) % WINDOW_SIZE;
            uncodedHead = (uncodedHead + 1) % MAX_CODED;
            len--;
            i++;
        }

        /* find match for the remaining characters */
        matchData = FindMatch(windowHead, uncodedHead, len);
    }

    /* write out any remaining encoded data */
    if (nextEncoded != 0)
    {
        putc(flags, outFile);
	compressedSize++;

        for (i = 0; i < nextEncoded; i++)
        {
            putc(encodedData[i], outFile);
	    compressedSize++;
        }
    }
    fprintf(stderr, "compressedSize %lx\n", compressedSize);
    while ((compressedSize % 0x10) != 0)
    {
        putc(0x00, outFile);
        compressedSize++;
    }
}

/****************************************************************************
*   Function   : DecodeLZSS
*   Description: This function will read an LZss encoded input file and
*                write an output file.  The encoded file uses a slight
*                modification to the LZss algorithm.  I'm not sure who to
*                credit with the slight modification to LZss, but the
*                modification is to group the coded/not coded flag into
*                bytes.  By grouping the flags, the need to be able to
*                write anything other than a byte may be avoided as longs
*                as strings encode as a whole byte multiple.  This algorithm
*                encodes strings as 16 bits (a 12bit offset + a 4 bit length).
*   Parameters : inFile - file to decode
*                outFile - file to write decoded output
*   Effects    : inFile is decoded and written to outFile
*   Returned   : NONE
****************************************************************************/
void DecodeLZSS(FILE *inFile, FILE *outFile)
{
    int  i, c;
    unsigned char flags, flagsUsed;     /* encoded/not encoded flag */
    int nextChar;                       /* next char in sliding window */
    encoded_string_t code;              /* offset/length code for string */

    /* initialize variables */
    flags = 0;
    flagsUsed = 7;
    nextChar = 0;

    /************************************************************************
    * Fill the sliding window buffer with some known vales.  EncodeLZSS must
    * use the same values.  If common characters are used, there's an
    * increased chance of matching to the earlier strings.
    ************************************************************************/
    for (i = 0; i < WINDOW_SIZE; i++)
    {
        slidingWindow[i] = ' ';
    }

    while (TRUE)
    {
        flags <<= 1;
        flagsUsed++;

        if (flagsUsed == 8)
        {
            /* shifted out all the flag bits, read a new flag */
            if ((c = getc(inFile)) == EOF)
            {
                break;
            }

            flags = c & 0xFF;
            flagsUsed = 0;
        }

        if ((flags & 0x80) == 0)
        {
            /* uncoded character */
            if ((c = getc(inFile)) == EOF)
            {
                break;
            }

            /* write out byte and put it in sliding window */
            putc(c, outFile);
            slidingWindow[nextChar] = c;
            nextChar = (nextChar + 1) % WINDOW_SIZE;
        }
        else
        {
            /* offset and length */
            if ((code.length = getc(inFile)) == EOF)
            {
                break;
            }

            if ((code.offset = getc(inFile)) == EOF)
            {
                break;
            }

            /* unpack offset and length */
            code.offset = (code.offset + ((code.length & 0x03) << 8));
	    code.offset = WINDOW_SIZE - code.offset;
            code.length = (code.length >> 2);

            /****************************************************************
            * Write out decoded string to file and lookahead.  It would be
            * nice to write to the sliding window instead of the lookahead,
            * but we could end up overwriting the matching string with the
            * new string if abs(offset - next char) < match length.
            ****************************************************************/
            for (i = 0; i < code.length; i++)
            {
                c = slidingWindow[(nextChar + code.offset + i) % WINDOW_SIZE];
                putc(c, outFile);
                uncodedLookahead[i] = c;
            }

            /* write out decoded string to sliding window */
            for (i = 0; i < code.length; i++)
            {
                slidingWindow[(nextChar + i) % WINDOW_SIZE] =
                    uncodedLookahead[i];
            }

            nextChar = (nextChar + code.length) % WINDOW_SIZE;
        }
    }
}
