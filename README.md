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

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, khoet 1 lo D5 tai X=20 mm va Y=15 mm"

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

The program displays the plan, hole-center coordinates, default assumptions and warnings. It asks for confirmation before invoking SOLIDWORKS.

## Hole placement conventions

- X follows the 100 mm length; Y follows the 60 mm width.
- XY coordinates are measured in mm from the lower-left origin of the top face.
- Two-hole pitch patterns are symmetric about the face center. The default direction is X; use "theo chieu rong" for Y.
- One hole without coordinates is proposed at the top-face center and this default is disclosed.
- Four corner holes without an explicit edge offset are proposed 10 mm from each adjacent edge and this default is disclosed.
- The program checks hole-to-edge, hole-to-Fillet/Chamfer and hole-to-hole clearance. Unsupported counts/layouts remain preview-only instead of being placed arbitrarily.

## Thread representation

ISO coarse metric M3 and M4 use their standard pitch and tap-drill diameter and are created as native SOLIDWORKS Hole Wizard tapped-hole features with a Through All thread end condition. They are not modeled as a true helical solid thread.

The code resolves the registered sldworks.tlb and early-binds IWizardHoleFeatureData2 before writing thread properties. CosmeticThreadType is read-only/not implemented as a setter in the SOLIDWORKS API version documented here, so cosmetic-thread display follows the installed SOLIDWORKS Hole Wizard/template defaults. The code does not claim to force a callout.

## Tests

    python -m unittest discover -s tests -v

GitHub Actions runs parser and geometry-planning tests on pushes to feature/natural-language-cad. They do not start SOLIDWORKS; Chamfer, Hole Wizard and COM calls still require verification in the Windows/SOLIDWORKS session.

## Units

User-facing dimensions are in mm. SOLIDWORKS geometry API values are converted to metres before COM calls.
