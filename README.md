# SOLIDWORKS Automation – Python COM

Dự án tự động tạo Part trong SOLIDWORKS bằng Python và COM API. Nhánh phát triển feature/natural-language-cad bổ sung hướng **Text-to-CAD**: nhập mô tả tiếng Việt, xem kế hoạch CAD, xác nhận rồi tạo khối cơ sở.

## Môi trường đã kiểm chứng cho starter gốc

- Windows, SOLIDWORKS 2026
- Python 3.14 64-bit
- pywin32
- VS Code

Các phiên bản khác có thể cần điều chỉnh COM API.

## Cấu trúc

    src/
      __init__.py
      create_box.py
      text_to_cad.py
      run_text_to_cad.py
    tests/
      test_text_to_cad.py
    docs/
      workflow.md
      troubleshooting.md
      natural-language-cad.md
    output/

## Cài đặt

Mở PowerShell tại thư mục dự án:

    py -3.14 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -r requirements.txt

Nếu cần tạo COM wrapper, chạy:

    python -m win32com.client.makepy

Chọn **SOLIDWORKS 2026 Type Library (22.0)**.

## Cách 1 – tạo hộp bằng script gốc

    python src/create_box.py

Mặc định tạo hộp 100 × 60 × 30 mm tại output/My_First_Part.SLDPRT.

## Cách 2 – Text-to-CAD

Ví dụ:

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm"

Hoặc chạy tương tác:

    python -m src.run_text_to_cad

Chương trình sẽ:
1. Phân tích câu mô tả và kiểm tra kích thước.
2. Hiển thị CAD plan để người dùng xem lại.
3. Hỏi xác nhận trước khi gọi SOLIDWORKS.
4. Tạo khối hộp cơ sở và lưu tại output/Generated_From_Text.SLDPRT.

Có thể chỉ định file đầu ra:

    python -m src.run_text_to_cad "Tao hop dai 120 mm rong 80 mm cao 40 mm" --output "output/Hop_120.SLDPRT"

### Giới hạn hiện tại

- Hỗ trợ khối hộp chữ nhật và kích thước dài/rộng/cao hoặc bộ ba 100 x 60 x 30 mm.
- Có thể trích xuất yêu cầu fillet, chamfer và lỗ thành CAD plan.
- **Fillet, chamfer và lỗ chưa được thực thi**; chương trình chỉ tạo khối hộp cơ sở và cảnh báo rõ điều này.
- Parser hiện dùng quy tắc, không gọi dịch vụ AI.
- Mô tả thiếu hoặc kích thước không hợp lệ sẽ bị từ chối, không tự đoán.

Chi tiết: docs/natural-language-cad.md.

## Chạy kiểm thử parser

    python -m unittest discover -s tests -v

Các bài test parser không cần SOLIDWORKS. Việc kiểm thử COM tạo hình vẫn cần môi trường SOLIDWORKS thực tế.

## Đơn vị

Thông số đầu vào dùng mm. Hàm mm_to_m() chuyển sang mét trước khi gọi SOLIDWORKS API.
