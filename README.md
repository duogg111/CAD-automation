# SOLIDWORKS Automation – Python COM

Dự án tạo Part tự động trong SOLIDWORKS bằng Python và COM API. Nhánh phát triển feature/natural-language-cad bổ sung Text-to-CAD: nhập mô tả tiếng Việt, xem kế hoạch, xác nhận rồi tạo hình.

## Môi trường baseline

- Windows, SOLIDWORKS 2026
- Python 3.14 64-bit
- pywin32
- VS Code

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

    py -3.14 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -r requirements.txt

Tạo COM wrapper nếu cần:

    python -m win32com.client.makepy

Chọn SOLIDWORKS 2026 Type Library (22.0).

## Text-to-CAD examples

Hộp cơ bản:

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm"

Fillet bốn cạnh đứng:

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, bo goc R5"

Chamfer bốn cạnh quanh mặt trên:

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, vat canh 2 mm"

Bốn lỗ xuyên, mặc định tâm cách mỗi mép 10 mm:

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, khoet 4 lo D3"

Chỉ định khoảng cách mép 8 mm:

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, khoet 4 lo D3 cach mep 8 mm"

Kết hợp Chamfer, Fillet và Hole:

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, vat canh 2 mm, bo goc R5, khoet 4 lo D3 cach mep 10 mm"

The program prints the planned feature targets, hole centers, defaults and warnings. It asks for confirmation before opening SOLIDWORKS operations.

## Feature behaviour

- Fillet R: four vertical outer corner edges.
- Chamfer: four edges surrounding the top face. It is applied before the vertical Fillet so the corner-edge selector can identify the shortened vertical edges.
- Four holes: four through-holes in a symmetric corner layout; each center is measured from the adjacent two footprint edges. If no edge offset is given, 10 mm is used and explicitly shown in the plan.
- Other hole counts/layouts: preview only; not silently positioned.
- Hole diameter and offsets are checked against the part footprint and Chamfer/Fillet clearances.

## Tests

    python -m unittest discover -s tests -v

Parser and geometry-planning tests do not require SOLIDWORKS. The COM calls that create Chamfer, Fillet and Cut-Extrude must still be run and verified on the Windows/SOLIDWORKS installation.

## Units

User-facing dimensions are in mm. SOLIDWORKS geometry API values are converted to metres before the COM calls.
