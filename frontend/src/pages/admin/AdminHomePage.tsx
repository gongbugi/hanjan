import { Link } from "react-router-dom";

const LINKS = [
  { to: "/admin/beans/new", title: "원두 등록", description: "봉투 사진에서 원두 정보를 채워요" },
  { to: "/admin/brews/new", title: "추출 기록", description: "레시피·만족도·맛 메모를 남겨요" },
  { to: "/admin/grind", title: "입도 측정", description: "가루 사진으로 입자 크기 분포를 재요" },
  { to: "/grinders", title: "그라인더", description: "그라인더 추가와 클릭 ↔ 입도 표" },
  { to: "/recommendations", title: "추천 새로 만들기", description: "내 기록으로 추천을 다시 만들어요" },
  { to: "/catalog", title: "신상 수집", description: "로스터리 신상을 지금 가져와요" },
];

export function AdminHomePage() {
  return (
    <>
      <h1>쓰기</h1>
      {LINKS.map((link) => (
        <Link key={link.to} to={link.to} className="card card-link">
          <strong>{link.title}</strong>
          <div className="muted">{link.description}</div>
        </Link>
      ))}
    </>
  );
}
