import io

import numpy as np
import pytest
from PIL import Image

from hanjan.grind.synthetic import synthetic_grind_image

pytestmark = pytest.mark.db


def png(img: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, "PNG")
    return buf.getvalue()


def measure(client, admin, *, d50: float, seed: int, **form):
    img, truth = synthetic_grind_image(np.full(350, d50), seed=seed)
    response = client.post(
        "/api/admin/grind/measurements", data=form, files={"file": ("g.png", png(img), "image/png")}, headers=admin
    )
    assert response.status_code == 201, response.text
    return response.json(), truth


def test_measurements_build_the_click_table_and_convert_a_target_size(client, admin):
    grinder = client.post("/api/admin/grinders", json={"name": "알리 핸드밀"}, headers=admin).json()
    m12, truth12 = measure(client, admin, d50=0.5, seed=12, grinder_id=grinder["id"], clicks=12)
    m24, _ = measure(client, admin, d50=0.9, seed=24, grinder_id=grinder["id"], clicks=24)
    assert m12["d50_mm"] == pytest.approx(float(np.median(truth12)), rel=0.03)

    cal = client.get(f"/api/grinders/{grinder['id']}/calibration").json()
    assert [row["clicks"] for row in cal["rows"]] == [12, 24]
    assert cal["monotonic"] is True

    target = (m12["d50_mm"] + m24["d50_mm"]) / 2
    suggestion = client.get(f"/api/grinders/{grinder['id']}/suggest", params={"target_d50_mm": target}).json()
    assert suggestion["clicks"] == 18


def test_measurement_reuses_the_brew_recipe(client, admin):
    grinder = client.post("/api/admin/grinders", json={"name": "알리 핸드밀"}, headers=admin).json()
    bean = client.post("/api/admin/beans", json={"name": "구지"}, headers=admin).json()
    brew = client.post(
        "/api/admin/brews",
        json={"bean_id": bean["id"], "grinder_id": grinder["id"], "grind_clicks": 20, "rating": 4},
        headers=admin,
    ).json()

    measurement, _ = measure(client, admin, d50=0.7, seed=7, brew_id=brew["id"])

    assert (measurement["grinder_id"], measurement["clicks"]) == (grinder["id"], 20)
    detail = client.get(f"/api/brews/{brew['id']}").json()
    assert [m["id"] for m in detail["measurements"]] == [measurement["id"]]


def test_photo_without_marker_is_422(client, admin):
    grinder = client.post("/api/admin/grinders", json={"name": "알리 핸드밀"}, headers=admin).json()
    blank = np.full((400, 400), 255, np.uint8)
    response = client.post(
        "/api/admin/grind/measurements",
        data={"grinder_id": grinder["id"], "clicks": 10},
        files={"file": ("g.png", png(blank), "image/png")},
        headers=admin,
    )
    assert response.status_code == 422
    assert "마커" in response.json()["detail"]
