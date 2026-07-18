import os

# 1. 윈도우 다운로드 경로 자동 설정
windows_user_profile = os.popen('cmd.exe /c "echo %USERPROFILE%"').read().strip()
if windows_user_profile:
    win_path = windows_user_profile.replace('\\', '/').replace(':', '')
    output_path = f"/mnt/{win_path[0].lower()}{win_path[1:]}/Downloads/H010"
else:
    output_path = "/mnt/c/Users/Public/Downloads/H010"

# 2. 데이터 정의 및 인코딩
header_bytes = "0910912026070001H0101087002514".encode('euc-kr')
data_body_bytes = "099920260700000100000004490000000001340000000000000000000003150000000000000000000000000000000004490000000000000000000000000000000000000000000004490000000001340000000003150000000000000".encode('euc-kr')

hospital_name = "\uc9c4\ub9e5\ud55c\uc758\uc6d0"  # '진맥한의원'
info_bytes = f"00000000000020260711{hospital_name}            {hospital_name}                    20001026".encode('euc-kr')

crlf = b'\r\n'
row_target_size = 346  # 줄바꿈(\r\n) 제외 순수 데이터 길이 346바이트 지정

# 3. [핵심] 각 행을 정확히 346바이트로 패딩한 뒤 줄바꿈을 붙임
padded_header = header_bytes.ljust(row_target_size, b' ') + crlf      # 346 + 2 = 348바이트
padded_body = data_body_bytes.ljust(row_target_size, b' ') + crlf      # 346 + 2 = 348바이트
padded_info = info_bytes.ljust(row_target_size, b' ') + crlf          # 346 + 2 = 348바이트

# 4. 세 행을 하나로 조립 (총 348 * 3 = 1044바이트)
final_bytes = padded_header + padded_body + padded_info

# 5. 전체 파일의 최대 규격이 2096바이트이므로, 남는 공간을 공백으로 채워 총 크기 맞춤
target_file_size = 2096
if len(final_bytes) < target_file_size:
    final_bytes = final_bytes.ljust(target_file_size, b' ')

# 6. 파일 쓰기
with open(output_path, "wb") as f:
    f.write(final_bytes)

print("SAM 파일 규격 변환 완료!")
print(f"-> 윈도우 생성 경로: {output_path}")
print(f"-> 최종 크기: {len(final_bytes)} 바이트 (행당 348바이트 정렬 완료)")