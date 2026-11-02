# SOLIDWORKS Automation – Python COM

Dự án tạo Part tự động trong SOLIDWORKS bằng Python và COM API. Nhánh feature/natural-language-cad phát triển Text-to-CAD: nhập mô tả tiếng Việt, xem kế hoạch, xác nhận rồi tạo hình.

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

Bốn lỗ xuyên ở bốn góc:

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, khoet 4 lo D3"

Một lỗ tại tọa độ X=20, Y=15 mm:

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, khoet 1 lo D5 tai X=20 Y=15"

Hai lỗ, cách tâm-tâm 40 mm theo chiều dài (trục X), đặt đối xứng quanh tâm mặt:

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, khoet 2 lo D5 cach nhau 40 mm"

Hai lỗ theo chiều rộng (trục Y):

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, khoet 2 lo D5 cach nhau 30 mm theo chieu rong"

Nhiều lỗ tại tọa độ tự chỉ định:

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, khoet 2 lo D5 tai (20, 15) va (80, 15)"

Một lỗ ren ISO M3 tại tâm mặc định:

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, lo ren M3"

Hai lỗ ren ISO M3 cách nhau 40 mm:

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, tao 2 lo ren M3 cach nhau 40 mm"

Một lỗ ren ISO M4 ở tọa độ cụ thể:

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, tao 1 lo ren M4 tai (20, 20)"

Kết hợp Chamfer, Fillet và Hole:

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, vat canh 2 mm, bo goc R5, khoet 4 lo D3 cach mep 10 mm"

The program prints the planned feature targets, hole centers, defaults and warnings. It asks for confirmation before invoking SOLIDWORKS.

## Feature behaviour

- Fillet R: four vertical outer corner edges.
- Chamfer: four edges surrounding the top face. It is applied before the vertical Fillet.
- Ordinary holes: circular sketch plus Cut-Extrude Through All.
- Hole positions: four-corner layout; explicit XY coordinates; one hole at the face center; or two holes centered around the face with a center-to-center distance along X or Y.
- Explicit XY coordinates are measured in mm from the lower-left origin of the top face, matching the base sketch's X/Y axes.
- Other hole counts/layouts are preview-only; the program does not guess positions.
- ISO metric tapped holes: M3 coarse (0.5 mm pitch, 2.5 mm tap drill) and M4 coarse (0.7 mm pitch, 3.3 mm tap drill), via Hole Wizard. Tap drill dimensions are loaded by the SOLIDWORKS ISO standard table.
- Hole Wizard tapped holes carry thread/cosmetic-thread information; they are not a true modeled helical solid thread.
- Hole positions are checked against part boundaries, Chamfer and rounded Fillet clearances.

## Tests

    python -m unittest discover -s tests -v

Parser and geometry-planning tests do not require SOLIDWORKS. The COM calls that create Chamfer, Fillet, Cut-Extrude and Hole Wizard features must be run and verified in the Windows/SOLIDWORKS installation.

## Units

User-facing dimensions are in mm. SOLIDWORKS geometry API values are converted to metres before COM calls.
