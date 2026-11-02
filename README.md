# SOLIDWORKS Automation – Python COM

Dự án tự động tạo Part trong SOLIDWORKS bằng Python và COM API. Nhánh feature/natural-language-cad bổ sung hướng Text-to-CAD: nhập mô tả tiếng Việt, xem kế hoạch CAD, xác nhận rồi tạo khối cơ sở.

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
      solidworks_features.py
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

Nếu cần tạo COM wrapper/constants, chạy:

    python -m win32com.client.makepy

Chọn SOLIDWORKS 2026 Type Library (22.0).

## Text-to-CAD

Tạo hộp đơn giản:

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm"

Tạo hộp và bo bốn cạnh đứng ngoài:

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, bo goc R5"

Chương trình hiển thị CAD plan và yêu cầu xác nhận trước khi gọi SOLIDWORKS. Fillet R5 được áp dụng cho bốn cạnh đứng ở bốn góc ngoài của hộp. Đây không phải lệnh bo tất cả 12 cạnh.

Chỉ định file đầu ra:

    python -m src.run_text_to_cad "Tao hop dai 120 mm rong 80 mm cao 40 mm, bo goc R5" --output "output/Hop_120.SLDPRT"

### Phạm vi hiện tại

- Hỗ trợ khối hộp chữ nhật và kích thước dài/rộng/cao hoặc bộ ba 100 x 60 x 30 mm.
- Fillet bán kính không đổi trên bốn cạnh đứng ngoài được triển khai bằng ISimpleFilletFeatureData2.
- Chamfer và holes mới chỉ được phân tích; chưa thực thi.
- Parser hiện dùng quy tắc, không gọi dịch vụ AI.
- Bán kính Fillet phải nhỏ hơn một nửa cạnh ngắn của mặt đáy.

## Chạy kiểm thử không cần SOLIDWORKS

    python -m unittest discover -s tests -v

Các bài test parser và bộ lọc hình học không gọi COM. Việc kiểm thử Feature Fillet thực tế vẫn cần SOLIDWORKS 2026 trên Windows.

## Đơn vị

Thông số đầu vào dùng mm. SOLIDWORKS API nhận đơn vị mét; code chuyển đổi trước khi gọi API.
