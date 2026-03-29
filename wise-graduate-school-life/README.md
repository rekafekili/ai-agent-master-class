# 슬기로운 대학원 생활

## 1. 에이전트 이름

슬기로운 대학원 생활(논문 읽기 어시스턴트)

## 2. 에이전트 목적

영어를 못하는 상황에서 해외 논문을 읽는건 정말 어려웠다. 그렇다고 번역기만 돌리자니 대학원을 다니고 있는 학생이 맞는건가 싶은 괴리감이 들었다. 어차피 논문을 쓰려면 AI를 사용하더라도 내용을 직접 검수해야하고, 그러려면 영어 능력은 필수적으로 높여야 한다. 다만, 논문을 읽다보면 참고 문헌의 어떤 부분을 참고 했는지 보고 싶어도 찾는데 시간이 꽤 걸리고, 어려운 영어 어휘나 표현이 나오면 그걸 찾다가 논문을 읽기 싫어지기도 한다. 그래서 한 번에 논문을 읽으면서 개인 역량도 키울 수 있는 에이전트가 있으면 좋겠다고 생각했다.

## 3. 핵심 기능(프로세스)

### PDF 파일 업로드

- 테스트 단계: `asset/MSCRS_ Multi-modal Semantic Graph Prompt Learning Framework for Conversational Recommender Systems.pdf` 파일 사용

### 논문 PDF -> 객체 변환

- 참고자료: [PDF to Markdown OpenSource Deep Dive](https://jimmysong.io/blog/pdf-to-markdown-open-source-deep-dive/)
- 빠른 프로세스 확립을 위해 `Marker-pdf` 라이브러리 사용

### 논문 객체에서 영단어 추출

- 논문 내용에서 영단어를 추출

## 4. 테스트

- `notebook.ipynb` 파일에서 코드 블록을 차례로 실행.
