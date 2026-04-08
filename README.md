# KAUTM 채용공고 RSS 피드

**한국산학기술학회(KAUTM)** 채용공고를 자동으로 수집하여 RSS 피드로 제공합니다.

## 📡 RSS 구독 주소

GitHub Pages를 활성화하면 아래 주소로 구독할 수 있습니다:

```
https://<your-github-username>.github.io/<repo-name>/rss.xml
```

## ⚙️ 동작 방식

- **GitHub Actions**가 하루 3번 (오전 9시, 오후 1시, 오후 6시 KST) 자동 실행
- 새 채용공고가 감지되면 `rss.xml`을 업데이트하고 커밋
- `state.json`에 이미 수집된 공고 ID를 저장하여 중복 방지

## 🚀 설정 방법

### 1. 저장소 생성
이 파일들을 GitHub 저장소에 업로드합니다.

### 2. GitHub Pages 활성화
- 저장소 → **Settings** → **Pages**
- Source: `Deploy from a branch`
- Branch: `main` / `/ (root)`
- **Save** 클릭

### 3. RSS 구독
RSS 리더(Feedly, Inoreader, NetNewsWire 등)에 아래 URL 추가:
```
https://<your-github-username>.github.io/<repo-name>/rss.xml
```

### 4. 수동 실행 (선택)
- 저장소 → **Actions** → `KAUTM 채용공고 RSS 업데이트` → **Run workflow**

## 📁 파일 구조

```
├── generate_rss.py          # RSS 생성 스크립트
├── .github/
│   └── workflows/
│       └── update_rss.yml   # GitHub Actions 워크플로우
├── rss.xml                  # 생성된 RSS 피드 (자동 업데이트)
├── state.json               # 수집 상태 저장 (자동 생성)
└── README.md
```

## 🔔 알림 받기

| 방법 | 설명 |
|------|------|
| **Feedly** | RSS URL 추가 후 모바일 푸시 알림 설정 |
| **Inoreader** | RSS 추가 후 필터링 알림 설정 가능 |
| **IFTTT** | RSS → 이메일/슬랙/카카오 연동 |
| **GitHub 이메일** | Actions 실패 시 자동 알림 (기본 제공) |
