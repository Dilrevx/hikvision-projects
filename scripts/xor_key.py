import argparse  # 导入 argparse 模块，用于处理命令行参数


def cyclic_left_shift(key_bytes):
    """
    将一个字节数组向左循环移动一位。
    例如 b'\x01\x02\x03' -> b'\x02\x03\x01'
    """
    return key_bytes[1:] + key_bytes[:1]


def decrypt_file(input_path, output_path, initial_key_hex):
    """
    使用循环移位的重复密钥对文件进行异或解密。

    Args:
        input_path (str): 加密的输入文件路径。
        output_path (str): 解密后的输出文件路径。
        initial_key_hex (str): 初始密钥的十六进制字符串。
    """
    try:
        # 将十六进制密钥字符串转换为 bytearray
        key = bytearray.fromhex(initial_key_hex.replace(" ", ""))
        key_len = len(key)
        print(f"[*] 初始密钥 (十六进制): {key.hex().upper()}")
        print(f"[*] 密钥长度: {key_len} 字节")

        # 以二进制模式打开输入和输出文件
        with open(input_path, "rb") as f_in, open(output_path, "wb") as f_out:
            block_num = 1
            while True:
                # 从输入文件中读取一个与密钥等长的数据块
                encrypted_block = f_in.read(key_len)

                # 如果数据块为空，说明已到达文件末尾
                if not encrypted_block:
                    break

                # print(f"[*] 正在处理第 {block_num} 个数据块...")

                # 创建一个 bytearray 来存储解密后的数据块
                decrypted_block = bytearray(len(encrypted_block))
                # 将加密数据块与当前密钥进行逐字节异或
                for i in range(len(encrypted_block)):
                    decrypted_block[i] = encrypted_block[i] ^ key[i]

                # 将解密后的数据块写入输出文件
                f_out.write(decrypted_block)

                # 为下一个数据块，将密钥向左循环移位一个字节
                key = cyclic_left_shift(key)
                block_num += 1

        print(f"\n[+] 解密成功！🎉")
        print(f"[*] 加密文件: '{input_path}'")
        print(f"[*] 解密文件已保存至: '{output_path}'")

    except FileNotFoundError:
        print(f"[!] 错误: 未找到输入文件 '{input_path}'")
    except Exception as e:
        print(f"[!] 发生未知错误: {e}")


if __name__ == "__main__":
    # 设置命令行参数解析器
    parser = argparse.ArgumentParser(
        description="使用块异或密码解密文件，密钥在每个块后循环移位。", formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--input_file", help="加密的输入文件路径 (例如: firmware_encrypted.bin)。")
    parser.add_argument("--output_file", help="保存解密后文件的路径 (例如: firmware_decrypted.bin)。")

    args = parser.parse_args()

    # 问题中提供的密钥
    KEY_HEX_STRING = "BA CD BC FE D6 CA DD D3 BA B9 A3 AB BF CB B5 BE"

    decrypt_file(args.input_file, args.output_file, KEY_HEX_STRING)
