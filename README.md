# SOLIDWORKS Automation – Python COM

Dự án mẫu tự động tạo một khối hộp chữ nhật trong SOLIDWORKS bằng Python và COM API.

## Kết quả

- Kích thước: **100 × 60 × 30 mm**
- Định dạng: `SLDPRT`
- File đầu ra: `output/My_First_Part.SLDPRT`

## Môi trường đã kiểm chứng

- Windows
- SOLIDWORKS 2026
- Python 3.14 64-bit
- `pywin32`
- VS Code

Đây là môi trường đã chạy thành công trong dự án gốc. Các phiên bản SOLIDWORKS/Python khác có thể cần điều chỉnh.

## Cấu trúc

```text
SolidWorks_Automation/
├── src/
│   └── create_box.py
├── docs/
│   ├── workflow.md
│   └── troubleshooting.md
├── output/
│   └── .gitkeep
├── .gitignore
├── requirements.txt
└── README.md
```

## Cài đặt

Mở PowerShell tại thư mục dự án:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Nếu PowerShell chặn kích hoạt môi trường ảo, có thể chạy Python trực tiếp:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Cấu hình COM Type Library (khi cần)

Nếu pywin32 báo lỗi MakePy hoặc không tạo được wrapper cho SOLIDWORKS:

```powershell
python -m win32com.client.makepy
```

Trong danh sách, chọn **SOLIDWORKS 2026 Type Library (22.0)**.

## Chạy chương trình

```powershell
python src/create_box.py
```

Đảm bảo SOLIDWORKS đã được cài đặt trên máy. Script sẽ kết nối/mở SOLIDWORKS, tạo Part, vẽ Sketch, Extrude, Rebuild và lưu file.

## Thay đổi kích thước

Mở `src/create_box.py` và sửa:

```python
LENGTH = 100.0
WIDTH = 60.0
HEIGHT = 30.0
```

Đơn vị đầu vào là mm. Hàm `mm_to_m()` chuyển sang mét trước khi truyền vào API.

## Lưu ý

- Tên `Front Plane` và `Sketch1` phụ thuộc template/ngôn ngữ và cấu trúc FeatureManager. Nếu template khác, cần kiểm tra lại tên feature.
- Không commit thư mục `.venv/`, file SOLIDWORKS tạm `~$...`, hoặc file đầu ra lớn nếu không cần thiết.
- Không coi các tham số COM là có thể dùng giống hệt trên mọi phiên bản. Hãy kiểm tra API Help của đúng phiên bản SOLIDWORKS đang dùng.
- Xem `docs/troubleshooting.md` để biết các lỗi đã gặp và cách xử lý đã xác minh.
