from collections import deque

class VolkswagenSecurity:
  register: int
  carry_flag: int = 0
  instruction_tape: bytearray
  instruction_pointer: int = 0
  for_pointers: deque = deque()
  for_iterations: deque = deque()

  def __init__(self, instruction_tape, seed):
    self.instruction_tape = instruction_tape
    self.register = seed

  def rsl(self):
    self.carry_flag = self.register & 0x80000000
    self.register = self.register << 1
    if(self.carry_flag):
      self.register = self.register | 0x1
    self.register = self.register & 0xFFFFFFFF
    self.instruction_pointer += 1

  def rsr(self):
    self.carry_flag = self.register & 0x1
    self.register = self.register >> 1
    if(self.carry_flag):
      self.register = self.register | 0x80000000
    self.instruction_pointer += 1

  def add(self):
    self.carry_flag = 0
    operands = self.instruction_tape[self.instruction_pointer + 1:self.instruction_pointer + 5]
    add_int = operands[0] << 24 | operands[1] << 16 | operands[2] << 8 | operands[3]
    output_register = self.register + add_int
    if (output_register > 0xffffffff):
      self.carry_flag = 1
      output_register = output_register & 0xffffffff
    self.register = output_register
    self.instruction_pointer += 5

  def sub(self):
    self.carry_flag = 0
    operands = self.instruction_tape[self.instruction_pointer + 1:self.instruction_pointer + 5]
    sub_int = operands[0] << 24 | operands[1] << 16 | operands[2] << 8 | operands[3]
    output_register = self.register - sub_int
    if (output_register < 0):
      self.carry_flag = 1
      output_register = output_register & 0xffffffff
    self.register = output_register
    self.instruction_pointer += 5

  def eor(self):
    operands = self.instruction_tape[self.instruction_pointer + 1:self.instruction_pointer + 5]
    xor_int = operands[0] << 24 | operands[1] << 16 | operands[2] << 8 | operands[3]
    self.register = self.register ^ xor_int
    self.instruction_pointer += 5

  def for_loop(self):
    operands = self.instruction_tape[self.instruction_pointer + 1:self.instruction_pointer + 2]
    self.for_iterations.appendleft(operands[0] - 1)
    self.instruction_pointer += 2
    self.for_pointers.appendleft(self.instruction_pointer)

  def next_loop(self):
    if(self.for_iterations[0] > 0):
      self.for_iterations[0] -= 1
      self.instruction_pointer = self.for_pointers[0]
    else:
      self.for_iterations.popleft()
      self.for_pointers.popleft()
      self.instruction_pointer += 1

  # bcc = branch conditional
  def bcc(self):
    operands = self.instruction_tape[self.instruction_pointer + 1:self.instruction_pointer + 2]
    skip_count = operands[0] + 2
    if(self.carry_flag == 0):
      self.instruction_pointer += skip_count
    else:
      self.instruction_pointer += 2

  # bra = branch unconditional
  def bra(self):
    operands = self.instruction_tape[self.instruction_pointer + 1:self.instruction_pointer + 2]
    skip_count = operands[0] + 2
    self.instruction_pointer += skip_count

  def finish(self):
    self.instruction_pointer += 1

  def execute(self):
    instruction_set = {
      0x81 : self.rsl,
      0x82 : self.rsr,
      0x93 : self.add,
      0x84 : self.sub,
      0x87 : self.eor,
      0x68 : self.for_loop,
      0x49 : self.next_loop,
      0x4A : self.bcc,
      0x6B : self.bra,
      0x4C : self.finish
    }
    while(self.instruction_pointer < len(self.instruction_tape)):
      instruction_set[self.instruction_tape[self.instruction_pointer]]()
    return self.register
