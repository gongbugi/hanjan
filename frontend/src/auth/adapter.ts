export type AuthUser = { uid: string };

/**
 * 인증 제공자 어댑터. 제공자를 바꿔도(Firebase → 다른 것) 화면 코드는 이 인터페이스만 본다.
 *
 * myWeb에서 Cognito로 옮길 때 어댑터의 구독 해제를 빈 함수로 둬서 누수 위험이 남았다.
 * subscribe가 돌려주는 해제 함수는 실제로 구독을 끊어야 한다.
 */
export interface AuthAdapter {
  /** SDK가 저장소에서 세션 복구를 끝낸 뒤 호출된다. 반환값은 구독 해제 함수. */
  subscribe(listener: (user: AuthUser | null) => void): () => void;
  signIn(): Promise<void>;
  signOut(): Promise<void>;
  getToken(): Promise<string | null>;
}
