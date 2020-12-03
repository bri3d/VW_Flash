# ASW Update Payload

As we know from reading [docs.md](docs.md) , we have a full arbitrary code execution primitive accomplished by simply overwriting a flash memory block which has already been written.

This primitive comes with restrictions: we can only flip bits upwards (as they're in unerased flash blocks), and we must copy data very, very slowly.

We'd like to escape this constrained ASW-patching environment to flash complete arbitrary code to Simos18. To do so we need two things: a way to patch CBOOT, and a patch for CBOOT which removes protection. Both are surprisingly easy. As documented in "docs," we could flash arbitrary code directly, we could patch CBOOT in flash, or we could patch CBOOT in RAM and jump into it.

Patching CBOOT in RAM is much safer and easier for several reasons:

* By patching in RAM, we can patch whatever we want - we are not limited to performing a full erase-and-copy or only flipping bits upwards.
* By using CBOOT to flash a new CBOOT directly, we maintain a degree of integrity checking. While we disable signature checking, CRC validation is still active and a terminated flashing session, dead battery, or other adverse condition is unlikely to brick an ECU.
* By patching in RAM, the patch becomes idempotent. We don't need to check whether or not the patch has been applied already, we don't risk the ECU bricking if the end-user reboots the ECU willy-nilly, and we have a lot of opportunity to develop and debug the patch.
* The size of the patch can be made very small, saving painstaking time transferring block data.

For the rest of this exercise, we will use the CBOOT from 8V0906259H__0001.frf . This CBOOT has header information `SC841-111SC8E0` and responds to the CBOOT Version PID with `SC8.1 C0 02 SC8.` We will also use the corresponding ASW, which has software structure/revision `O20`. My recommended approach is to flash 8V0906259H__0001 onto your ECU, patch it, and then flash whatever altered software you would like. To apply this information to another CBOOT and ASW combination, we will need to locate the engineering mode / verification disable functions, which can be located by searching for XREFs to B000218C, we will need to re-locate a suitable nop area to inject our patch, and we will need to adjust the location of the function calls in the patch (to enable supervisor mode, alter the vector table, and so on). To do this, I recommend starting with a disassembly of 8V0906259H__0001 and re-applying the patches accordingly using a disassembly of the other software. Some more automated "needle" based patching is coming as most procedures are quite recognizable, but of course is always fraught with peril.

Back to patching: we need to learn to load CBOOT into RAM, but this is easy as CBOOT does it on its own. If we take a look at 8001dd26 in the 8V0906259H__0001 CBOOT, we see a procedure for loading CBOOT into RAM. The mechanics are documented line-by-line below, but are really quite simple and consist of resetting the peripheral controllers, resetting the task context base, moving the trap vector, and finally copying the new CBOOT and jumping into it. Because we essentially "stop" the rest of ASW execution, we don't have to be overly careful about where we jump into the patch from, and because most of the code is available to us in CBOOT, we don't have to do a whole lot. 

Next, we need to figure out how to disable RSA validation. Once we load CBOOT into RAM in our disassembly tool of choice, it becomes easier to follow and we can start to locate the validity checking mechanisms. We know the ECU performs the validation when the Checksum Remote Routine is invoked, so we can follow the Checksum Remote Routine handler at 8002e9d2 deep into the abyss. Eventually, we land on a remarkably simple function at 80024cf6, which quite literally sets a flag to `0` or `1`. If this flag is set to "1," most validation is simply bypassed, in several locations. How convenient!

Upon some additional inspection of this function and its references, this appears to be some form of "engineering mode" or "development" flag check. The function itself seems to compare a summation algorithm applied against the Device ID bytes loaded into RAM at boot (or the OTP area later) and set this flag if they match a specific value.

The nice part about this function is that while it lives in many places across different CBOOT revisions, it seems to always reference b000218c and set it to the "development mode" value. So, by searching for XREFs to b000218c and patching the resultant function, you can enable this "engineering/development" mode freely in pretty much any CBOOT revision.

There is the same function repeated earlier in the CBOOT at 8001cee4 to run from PMEM. We need to patch this method too, in the next CBOOT we pass in (which will eventually be flashed). This has some other handy side effects in terms of enabling some extra permissions in CAN handlers and around various other parts of the software. However, in our CBOOT-on-CBOOT world, this function isn't even loaded into RAM and we can't (and don't need) to patch it this time around.

So, here's the code to load, patch, and jump into an RSA Off CBOOT from a running ASW. Now it needs a home. We can write-without-erasing any ASW block, and because the CBOOT-loader resets task execution, we can jump into it from most places in ASW. Due to the glacially slow pace at which our write primitive operates, it would be best if we could choose the smallest ASW block - that's `ASW3`.

There's a giant sea of free space at the end of ASW3, so finding a place for the function to live is easy, especially given it's so small. We can pick an arbitrary location on a 256-byte block boundary, like 808fd00. We need to place the code on a block boundary because the flash is programmed in 256-byte "assembly pages." While we are transmitting "no change" (0 areas) to be flashed, we can stuff the entire assembly page buffer, but to make sure the bit flips soak since we didn't erase flash, we need to "slow down" when we reach the area we are overwriting and flash it only 8 bytes at a time.

Next up, we need to write a "hook" to jump into our new function from running ASW code. In my O20 version ASW3, there's a nice task initialization function starting at 8088962c with a big long sled of nop at 8088965c. Searching for isync and dsync instructions is useful to locate these sort of initialization functions which are likely to also contain nop sleds. This particular nop sled is so long that you can put pretty much whatever you want there, really - either a short position-dependent call instruction or even a full blown load-and-call.

There's also a truly enormous sea of free space to add the function to near the end of ASW3.

Assuming we pick 808fdd00 as the free space to overwrite with the function and we want to boundary-align our patch,

```
80889660 91 00 09 f8     movh.a     a15,#0x8090
80889664 d9 ff c0 4d     lea        a15,[a15]-0x2300
80889668 2d 0f 00 00     calli      a15=>FUN_808fdd00
```

Does the trick well, with the added advantage that this "hook" is also position independent and can be made to live in any available nop area if you wish.

Please check your CBOOT carefully for strings that look like this:

* `10310096AA------NB0` : This is the hardware correlation identifier required by SBOOT. It should be the same for most SIMOS18 ECUs.
* `SC841-111SC8E0` : This is the software correlation identifier required to build a full ASW. If your CBOOT has this header, there's a good chance it matches the sample used in this exercise.
* `SC8.1 C0 02 SC8.` : This is the CBOOT software identifier. 

If you plan to use this exact hook, please also check you are patching over ASW version `O20` as well. This can be identified from the other part of the software correlation identifier - for example, at the end of: `111SC8E0O20`

```
91 20 00 c8     movh.a     a12,#0x8002 // we're gonna use relative addressing from 0x80020000, set it up
91 00 00 4d     movh.a     a4,#0xd000 // about to set task context base to DAT_d0000440
d9 44 40 10     lea        a4=>DAT_d0000440,[a4]0x440 // set task context base to DAT_d0000440                        
d9 cf ee 9d     lea        a15,[a12]-0x2192 // 8002 - 2192 = 8001de6e SET_TASK_CONTEXT PCXI register
2d 0f 00 00     calli      a15=>SET_TASK_CONTEXT 0x8001de6e // this function manipulates the PCXI register to set the task context for the running task                     
d9 cf fe 2d     lea        a15,[a12]-0x2342 // 8002 - 2342 = 8001dcbe RESET STM PERIPHERAL 
3b 00 20 41     mov        d4,#0x1200 // param 1 = 0x1200 // set parameter to same as original CBOOT loader
2d 0f 00 00     calli      a15=>RESET_STM    // RESET STM 0x8001dcbe. This function resets the STM peripheral                        
d9 cf 06 7e     lea        a15,[a12]-0x1e3a // 8002 - 1e3a = 8001e1c6 RESET MSC PERIPHERAL. 
3b 00 20 41     mov        d4,#0x1200 // param 1 = 0x1200 //  make sure d4 didn't get clobbered,  same 0x1200 param
2d 0f 00 00     calli      a15=>RESET_MSC // RESET MSC 0x8001e1c6. This function resets the MSC peripheral   
d9 cf fe 4c     lea        a15, [a12]-0x32C2 ENTER_SUPERVISOR_MODE
2d 0f 00 00     calli      ENTER_SUPERVISOR_MODE // 8001cd3e ENTER SUPERVISOR MODE TO RESET TRAP VECTOR. This function messes with some voodoo stuff to enter tricore "supervisor mode"
0d 00 c0 04     isync      // necessary before resetting trap vector
91 00 00 fc     movh.a     a15,#0xc000 // reset system register fe24 (trap vector table) to 0xc0007b00
d9 ff 80 c7     lea        a15,[a15]0x7b00 // lower half
80 f0           mov.d      d0,a15 // move addr to reg
0d 00 80 04     dsync      // avoid data hazard when setting trap vector table
cd 40 e2 0f     mtcr       #0xfe24,d0 // set control register fe24 reset trap vector
0d 00 c0 04     isync      // necessary after resetting trap vector
0d 00 c0 04     isync      // necessary after resetting trap vector
d9 cf e4 5c     lea        a15, [a12]-0x329C EXIT SUPERVISOR MODE
2d 0f 00 00     calli      FUN_8001cd64 // EXIT SUPERVISOR MODE. This function flips around to exit supervisor mode.
91 20 00 28     movh.a     a2,#0x8002 // pflash source high side
d9 22 00 02     lea        a2,[a2]0x2000 // pflash source low side -> 80022000
91 10 00 fd     movh.a     a15,#0xd001 // memory target high side
d9 ff 00 08     lea        a15,[a15]-0x8000 // memory target low side -> d0008000
91 10 00 50     movh.a     a5,#0x1 // high side of 162ff
d9 55 3f b6     lea        a5,[a5]0x62ff // we are going to copy 162ff bytes
09 22 01 00     ld.b       d2,[a2+]0x1=>LAB_80022000 // load from PFLASH pointer in a2
24 f2           st.b       [a15+]=>LAB_d0008000,d2 // store to RAM in a15
fc 5d           loop       a5,LAB_808fddb6 // loop 0x162ff times          
91 10 00 fd     movh.a     a15,#0xd001 // high side
d9 ff de 4a     lea        a15,[a15]-0x52e2 // load up d000ad1e into a15
c6 00           xor        d0, d0 // zero d0
74 f0           st.w       [a15], d0 // patch 0xd000ad1e from 3c 02 to 00 00. patching this JMP to a NOP causes the  sigcheck function used to verify CBOOT at d000acf6 to return 1 instead of 0, indicating the block is valid. "RSA Off!"
3b 00 20 41     mov        d4,#0x1200 // param 0 -> 0x1200
91 10 00 fd     movh.a     a15,#0xd001 // load d0008000
99 ff 00 08     ld.a       a15,[a15]-0x8000=>LAB_d0008000 // load CBOOT entry pointer from RAM
2d 0f 00 00     calli      a15 // enter CBOOT
00 90           ret // done
```
