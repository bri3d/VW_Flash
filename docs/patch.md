# ASW Update Payload

As we know from reading [docs.md](docs.md) , we have a full arbitrary code execution primitive accomplished by simply overwriting a flash memory block which has already been written.

This primitive comes with restrictions: we can only flip bits upwards (as they're in unerased flash blocks), and we must copy data 8 bytes at a time to avoid an ECC mismatch.

We'd like to escape this constrained ASW-patching environment to flash complete arbitrary code to Simos18. To do so we need two things: a way to patch CBOOT, and a patch for CBOOT which removes protection. Both are surprisingly easy. As documented in "docs," we could flash arbitrary code directly, we could patch CBOOT in flash, or we could patch CBOOT in RAM and jump into it.

Patching CBOOT in RAM is much safer and easier for several reasons:

* By patching in RAM, we can patch whatever we want in the code that executes - we are not limited to performing a full erase-and-copy or only flipping bits upwards.
* By using CBOOT to flash a new CBOOT directly, we maintain a degree of integrity checking. While we disable signature checking, CRC validation is still active and a terminated flashing session, dead battery, or other adverse condition is unlikely to brick an ECU.
* By patching in RAM, the patch becomes idempotent. We don't need to check whether or not the patch has been applied already, we don't risk the ECU bricking if the end-user reboots the ECU willy-nilly, and we have a lot of opportunity to develop and debug the patch.
* The size of the patch can be made very small, saving painstaking time transferring block data.

For the rest of this exercise, we will use the CBOOT from 8V0906259H__0001.frf . This CBOOT has header information `SC841-111SC8E0` and responds to the CBOOT Version PID with `SC8.1 E0 02 SC8.` We will also use the corresponding ASW, which has software structure/revision `O20`. My recommended approach is to flash 8V0906259H__0001 onto your ECU, patch it, and then flash whatever altered software you would like. To apply this information to another CBOOT and ASW combination, we will need to locate the engineering mode / verification disable functions, which can be located by searching for XREFs to B000218C, we will need to re-locate a suitable nop area to inject our patch, and we will need to adjust the location of the function calls in the patch (to enable supervisor mode, alter the vector table, and so on). To do this, I recommend starting with a disassembly of 8V0906259H__0001 and re-applying the patches accordingly using a disassembly of the other software. Some more automated "needle" based patching is coming as most procedures are quite recognizable, but of course is always fraught with peril.

Back to patching: we need to learn to load CBOOT into RAM, but this is easy as CBOOT does it on its own. The mechanics are documented line-by-line below, but are really quite simple and consist of resetting the peripheral controllers, resetting the task context base, moving the trap vector, and finally copying the new CBOOT and jumping into it. Because we essentially "stop" the rest of ASW execution, we don't have to be overly careful about where we jump into the patch from, and because most of the code is available to us in CBOOT, we don't have to do a whole lot. 

Next, we need to figure out how to disable RSA validation. Once we load CBOOT into RAM in our disassembly tool of choice, it becomes easier to follow and we can start to locate the validity checking mechanisms. We know the ECU performs the validation when the Checksum Remote Routine is invoked, so we can follow the Checksum Remote Routine handler. Eventually, we land on a remarkably simple function at 80024cf6, which quite literally sets a flag to `0` or `1`. If this flag is set to "1," most validation is simply bypassed, in several locations. How convenient!

Upon some additional inspection of this function and its references, this is the "Sample" flag check, to determine whether an ECU is a series-production ECU or a Sample one. The function itself applies a summation algorithm against the Device ID bytes loaded into RAM at boot, compares them to the values in the OTP area, and set a flag if they match a specific value. This has some additional side-effects as well, for example the `VW Logical Software Block Version` will respond with `X999` for each block's version. It may be appealing to turn Sample mode on in ASW as well, but this will not work without some additional hacking as in the ASW, Sample Mode changes the DFLASH / emulated EEPROM encryption strategy. In CBOOT, however, turning sample mode on seems to be a safe way to enable free reflashing.

The nice part about this Sample mode function is that while it lives in many places across different CBOOT revisions, it seems to always reference b000218c and set it to the "Sample" value. So, by searching for XREFs to b000218c and patching the resultant function, you can enable this "engineering/development" mode freely in pretty much any CBOOT revision.

There is the same function repeated earlier in the CBOOT as a library function in PMEM. We need to patch this method too, in the next CBOOT we pass in. However, in our CBOOT-on-CBOOT world, this function isn't even loaded into RAM and we can't (and don't need) to patch it this time around, so only one patch is necessary.

So, here's the code to load, patch, and jump into an RSA Off CBOOT from a running ASW. Now it needs a home. We can write-without-erasing any ASW block, and because the CBOOT-loader resets task execution, we can jump into it from most places in ASW. Due to the glacially slow pace at which our write primitive operates, it would be best if we could choose the smallest ASW block - that's `ASW3`.

There's a giant sea of free space at the end of ASW3, so finding a place for the function to live is easy, especially given it's so small. We can pick an arbitrary location on a 256-byte block boundary, like 808fd00. We need to place the code on a block boundary because the flash is programmed in 256-byte "assembly pages." While we are transmitting "no change" (0 areas) to be flashed, we can stuff the entire assembly page buffer, but to make sure the bit flips validate correctly with ECC since we didn't erase flash, we need to "slow down" when we reach the area we are overwriting and flash it only 8 bytes at a time.

Next up, we need to write a "hook" to jump into our new function from running ASW code. In my O20 version ASW3, there's a nice task initialization function starting at 8088962c with a big long sled of nop at 8088965c. Searching for isync and dsync instructions is useful to locate these sort of initialization functions which are likely to also contain nop sleds. This particular nop sled is so long that you can put pretty much whatever you want there, really - either a short position-dependent call instruction or even a full blown load-and-call.

Also importantly, this function already disables interrupts. If you move your patch elsewhere, you will need to add a `disable` instruction to the beginning to prevent ASW scheduled tasks from interfering with our CBOOT load-and execution. 

Assuming we pick 808fdd00 as the free space to overwrite with the function and we want to boundary-align our patch,

```
80889660 91 00 09 f8     movh.a     a15,#0x8090
80889664 d9 ff c0 4d     lea        a15,[a15]-0x2300
80889668 2d 0f 00 00     calli      a15=>FUN_808fdd00
```

functions as our hook, with. This "hook" assembler is also position independent and can be made to live in any available nop area if you wish, with the caveat that a `disable` may be required at another hook location.

Please check your CBOOT carefully for strings that look like this:

* `10310096AA------NB0` : This is the hardware correlation identifier required by SBOOT. It should be the same for most SIMOS18 ECUs.

* `SC841-111SC8E0` : This is the software correlation identifier required to build a full ASW. If your CBOOT has this header, there's a good chance it matches the sample used in this exercise.

* `SC8.1 E0 02 SC8.` : This is the CBOOT software identifier. This confirms that the CBOOT in use is an E0 CBOOT. 

If you plan to use this exact hook, please also check you are patching over ASW version `O20` as well. This can be identified from the other part of the software correlation identifier - for example, at the end of: `111SC8E0O20`

```
        808fdd00 91 20 00 c8     movh.a     a12,#0x8002 // we're gonna use relative addressing from 0x80020000, set it up
        808fdd04 91 00 00 4d     movh.a     a4,#0xd000 // about to set task context base to DAT_d0000440
        808fdd08 d9 44 40 10     lea        a4=>DAT_d0000440,[a4]0x440 // d0000440
        808fdd0c d9 cf 42 ae     lea        a15,[a12]-0x197e // setup call location
        808fdd10 2d 0f 00 00     calli      a15=>SUB_8001e682 // SET_TASK_CONTEXT : this function manipulates the PCXI register to set the task context for the running task 
        808fdd14 d9 cf 52 3e     lea        a15,[a12]-0x1b2e // reset STM (timer) peripheral function location
        808fdd18 3b 00 20 41     mov        d4,#0x1200 // 0x1200 -> reboot into Programming Mode argument
        808fdd1c 2d 0f 00 00     calli      a15=>SUB_8001e4d2 // CONFIGURE_TIMERS
        808fdd20 d9 cf 9a 7e     lea        a15,[a12]-0x1626 // load Reset MSC peripheral function location
        808fdd24 3b 00 20 41     mov        d4,#0x1200 // 0x1200 -> arg for Programming Mode
        808fdd28 2d 0f 00 00     calli      a15=>SUB_8001e9da // RESET_MSC_PERIPHERAL
        808fdd2c d9 cf 28 df     lea        a15,[a12]-0xc98 // ENABLE_ENDINIT location
        808fdd30 2d 0f 00 00     calli      a15=>SUB_8001f368 // ENABLE_ENDINIT: this function sets the Tricore ENDINIT bit using the watchdog password
        808fdd34 0d 00 c0 04     isync
        808fdd38 91 00 00 fc     movh.a     a15,#0xc000 // reconfigure trap vectors to point to 0xc0007b00
        808fdd3c d9 ff 80 c7     lea        a15,[a15]0x7b00
        808fdd40 80 f0           mov.d      d0,a15
        808fdd42 0d 00 80 04     dsync
        808fdd46 cd 40 e2 0f     mtcr       #0xfe24,d0 // 0xfe24 is the Trap Vector register
        808fdd4a 0d 00 c0 04     isync
        808fdd4e 0d 00 c0 04     isync
        808fdd52 d9 cf 0e ef     lea        a15,[a12]-0xc72 // DISABLE_ENDINIT location
        808fdd56 2d 0f 00 00     calli      a15=>SUB_8001f38e // DISABLE_ENDINIT: this function disables ENDINIT permissions
        808fdd5a 91 20 00 28     movh.a     a2,#0x8002 // Copy source address: 80022000
        808fdd5e d9 22 00 02     lea        a2,[a2]0x2000 // low half of source addr
        808fdd62 91 10 00 fd     movh.a     a15,#0xd001 // Copy dest address: d0008000
        808fdd66 d9 ff 00 08     lea        a15,[a15]-0x8000 // low half of dest addr
        808fdd6a 91 10 00 50     movh.a     a5,#0x1 // 0x162FF bytes to copy
        808fdd6e d9 55 3f b6     lea        a5,[a5]0x62ff // lower half of 0x162FF
                             LAB_808fdd72                                    XREF[1]:     808fdd78(j)  
        808fdd72 09 22 01 00     ld.b       d2,[a2+]0x1=>DAT_80022000 // Load data from Flash
        808fdd76 24 f2           st.b       [a15+]=>DAT_d0008000,d2 // store data to RAM                          
        808fdd78 fc 5d           loop       a5,LAB_808fdd72 // loop until done
        808fdd7a 91 10 00 fd     movh.a     a15,#0xd001 // Address to patch in RAM to enable Sample Mode: D000AD5E
        808fdd7e d9 ff dc 5a     lea        a15,[a15]-0x52a4 // low half of RAM addr
        808fdd82 c6 00           xor        d0,d0 // easy way to set to 0
        808fdd84 74 f0           st.w       [a15]=>DAT_d000ad5c,d0   // perform patch                       
        808fdd86 3b 00 20 41     mov        d4,#0x1200 // set 0x1200 Programming Mode parameter
        808fdd8a 91 10 00 fd     movh.a     a15,#0xd001 // upper part of entry point address
        808fdd8e 99 ff 00 08     ld.a       a15,[a15]-0x8000=>DAT_d0008000  // load entry point address            
        808fdd92 2d 0f 00 00     calli      a15 // jump in
        808fdd96 00 90           ret
        808fdd98 6B 6A 01 3E// This value fixes the CRC for the block


```

Finally, we need to do one more thing: we need to fix the CRC of the patched ASW block, as it is verified even with the Valid blocks still set. 

To do this, we use the tool `crchack` - we copy our patched bytes into the ASW3 binary, and then point `crchack` to a free data region, provide it the desired checksum for the block, and let it run. In this case, for example, copy the checksummed region of the file (0x300 - 0x7f9ff) and then run `crchack -x 00000000 -i 00000000 -w 32 -p 0x4c11db7 -b 514712:514716 ASW3.bin 0x7BA98379 > ASW3_Patched.bin`

Then we need to diff the binary with the original and copy the calculated CRC "fixer" value back in.

For this exact FRF file as the starting file, the "corrected" CRC value if applied immediately after the code patch is `6B 6A 01 3E`, so we add it immediately after the data in the patch. 

For Simos18.10, the principles and process are identical but addresses differ - the CBOOT which is loaded into RAM consists of 0x1C000 bytes of data copied from 0x80803BE0 (the new location of CBOOT in Simos18.10) to 0xB0004000 (LMURAM rather than Data Scratchpad RAM - presumably because there is such a massive amount of free LMURAM on the CPUs used in Simos18). A patch to `5G0906259Q__0005` is provided as `patch_1810.bin` .