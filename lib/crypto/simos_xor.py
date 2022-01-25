from lib.crypto.crypto_interface import CryptoInterface

# This is one of the silliest "encryption" methods I have ever seen.
# The code for this amazing algorithm was discovered at 80017168 in 03F906070AK.
# It could also have been found easily through some basic cryptanalysis.


class SimosXor(CryptoInterface):
    def decrypt(self, data: bytes) -> bytes:
        """Decrypt data using the Simos XOR scheme"""
        output_data = bytearray()
        counter = 0
        for data_byte in data:
            if counter == 256:
                counter = 0
            output_data.append(data_byte ^ counter)
            counter += 1
        return bytes(output_data)

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data using the Simos XOR scheme"""
        return self.decrypt(data)
