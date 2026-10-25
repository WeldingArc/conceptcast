"""Language packs: on-screen UI strings + narration phrases + spoken-symbol rules.

Built-in packs: en, ko. For any other language, don't edit this file in your installed copy
(it is a git clone): put translations in the course file instead.

    python3 scripts/build.py --print-strings en > strings.json

prints every key ({"ui": ..., "phrases": ..., "symbols": ...}); translate the values and paste
them into course.json as "ui", "phrases" and "symbols". build.py refuses to build a language
without a pack until every key is translated (or "allowEnglishFallback": true is set).
Keys ending in "_one" are the singular form used when {n} is 1.
To share a language with everyone, add it here as a new pack and send a pull request.
"""

UI = {
    "en": {
        "ddayLeft": "{n} days left", "ddayLeft_one": "1 day left", "ddayToday": "Exam day", "ddayPast": "Exam done",
        "fromStart": "{name} from the start", "heroStart": "Start here",
        "heroWrapped": "You've seen all {n} chapters · go again", "heroWrapped_one": "You've seen the chapter · go again", "heroResume": "Continue",
        "heroHint": "Press play, then just watch and listen. It moves on by itself.",
        "restartFrom": "Restart from {first}", "speed": "Speed", "voiceSample": "Hear the voice",
        "voiceSelect": "Choose voice", "recordedVoice": "Recorded voice", "systemVoiceSuffix": " (built-in)",
        "voiceBlockedNote": "The browser blocked the voice. Press play again to retry.",
        "noVoiceNote": "No voice found for this language. Screens advance at reading speed.",
        "weakBtn": "Replay {n} missed concepts → re-check", "weakBtn_one": "Replay 1 missed concept → re-check", "chapters": "Chapters",
        "conceptsN": "{n} concepts", "conceptsN_one": "1 concept", "seenStat": "Seen {a}/{b}", "checkStat": "Recall {r}/{n} ({p}%)",
        "missedStat": "Missed {n}", "watch": "Watch", "recall": "Recall check", "recheck": "Re-check",
        "keysHint": "Keys: Space play/pause · ← → back/next · Esc home",
        "voiceOn": "Voice on", "voiceOff": "Voice off", "home": "Home", "homeBtn": "Home",
        "restartConcept": "Restart this concept", "prev": "Back", "play": "Play", "next": "Next", "pause": "Pause",
        "chapterKick": "Chapter {n}", "chapterDone": "{name} done",
        "chapterDoneSub": "You've seen all {n} concepts. Now let's check what stuck.",
        "chapterDoneSub_one": "You've seen the concept. Now let's check what stuck.",
        "startRecall": "Start recall check ({n} questions)", "startRecall_one": "Start recall check (1 question)", "nextChapter": "Next: {name}",
        "listEnd": "Replay done", "listEndSub": "Let's re-check the {n} concepts you just saw.", "listEndSub_one": "Let's re-check the concept you just saw.",
        "startRecheck": "Start re-check", "conceptKick": "{chapter} · Concept {n}",
        "hookLabel": "Remember it like this", "termsLabel": "Exact terms to use", "exLabel": "Example from the notes",
        "defLabel": "Definition · use as written", "warnLabel": "Don't mix this up", "winDefault": "Stronger",
        "vs": "VS", "triangleAria": "Triangle diagram", "replayLabel": "Replay", "sceneStart": "Start", "sceneEnd": "End",
        "voiceOffAria": "Turn voice off", "voiceOnAria": "Turn voice on", "noVoiceAria": "No voice",
        "noVoiceTitle": "No voice available in this browser",
        "quizOX": "True / False", "quizMC": "Multiple choice", "conceptChip": "Concept · {t}",
        "correct": "Correct", "wrong": "Not quite", "answerIs": "Answer: {a}",
        "hintOX": "Keys: T or O = true, F or X = false", "hintMC": "Keys: 1–{n}", "oxKeysTrue": "TO", "oxKeysFalse": "FX",
        "seeResult": "See results", "nextQ": "Next question", "result": "Results",
        "band90": "Solid. Keep it up.", "band70": "Almost there. Just the missed ones once more.",
        "bandLow": "That's fine. Replay the missed concepts and try again.",
        "replayMissed": "Replay {n} missed concepts", "replayMissed_one": "Replay 1 missed concept", "voiceSwitched": "I'll read with this voice.",
        "oxTrue": "True", "oxFalse": "False",
    },
    "ko": {
        "ddayLeft": "D-{n}", "ddayToday": "D-DAY", "ddayPast": "시험 끝",
        "fromStart": "{name} 처음부터", "heroStart": "여기서 시작",
        "heroWrapped": "{n}개 챕터를 다 봤어요 · 한 바퀴 더", "heroResume": "이어서 보기",
        "heroHint": "누르고 그냥 보고 들으세요. 알아서 넘어가요.",
        "restartFrom": "처음({first})부터 다시", "speed": "속도", "voiceSample": "목소리 듣기",
        "voiceSelect": "목소리 선택", "recordedVoice": "녹음 목소리", "systemVoiceSuffix": " (기본 목소리)",
        "voiceBlockedNote": "브라우저가 목소리를 막았어요. 재생 버튼을 한 번 더 누르면 다시 시도해요.",
        "noVoiceNote": "이 브라우저에서 이 언어의 목소리를 찾지 못했어요. 화면이 읽는 속도에 맞춰 자동으로 넘어가요.",
        "weakBtn": "틀렸던 개념 {n}개 다시 보기 → 다시 확인", "chapters": "챕터",
        "conceptsN": "개념 {n}개", "seenStat": "본 개념 {a}/{b}", "checkStat": "기억 확인 {r}/{n} ({p}%)",
        "missedStat": "틀린 개념 {n}", "watch": "보기", "recall": "기억 확인", "recheck": "다시 확인",
        "keysHint": "키보드: 스페이스 재생/멈춤 · ← → 이전/다음 · Esc 홈",
        "voiceOn": "목소리 켬", "voiceOff": "목소리 끔", "home": "홈으로", "homeBtn": "홈",
        "restartConcept": "이 개념 처음부터", "prev": "이전", "play": "재생", "next": "다음", "pause": "멈춤",
        "chapterKick": "{n}장", "chapterDone": "{name} 끝",
        "chapterDoneSub": "개념 {n}개를 다 봤어요. 이제 머리에 남았는지 확인해요.",
        "startRecall": "기억 확인 시작 ({n}문제)", "nextChapter": "다음: {name}",
        "listEnd": "다시 보기 끝", "listEndSub": "방금 본 {n}개 개념을 다시 확인해요.",
        "startRecheck": "다시 확인 시작", "conceptKick": "{chapter} · 개념 {n}",
        "hookLabel": "이렇게 기억하세요", "termsLabel": "답안에 쓸 용어", "exLabel": "노트 속 예",
        "defLabel": "노트 정의 · 답안에 그대로", "warnLabel": "헷갈리지 말 것", "winDefault": "더 강함",
        "vs": "VS", "triangleAria": "삼각형 그림", "replayLabel": "다시 보기", "sceneStart": "시작", "sceneEnd": "끝",
        "voiceOffAria": "목소리 끄기", "voiceOnAria": "목소리 켜기", "noVoiceAria": "목소리 없음",
        "noVoiceTitle": "이 브라우저에 목소리가 없어요",
        "quizOX": "O / X", "quizMC": "객관식", "conceptChip": "개념 · {t}",
        "correct": "정답", "wrong": "오답", "answerIs": "정답: {a}",
        "hintOX": "O·X 키로도 고를 수 있어요", "hintMC": "1–{n} 키로도 고를 수 있어요", "oxKeysTrue": "O", "oxKeysFalse": "X",
        "seeResult": "결과 보기", "nextQ": "다음 문제", "result": "결과",
        "band90": "탄탄해요. 이대로 가면 돼요.", "band70": "거의 다 왔어요. 틀린 것만 한 번 더.",
        "bandLow": "괜찮아요. 틀린 개념만 다시 보면 돼요.",
        "replayMissed": "틀린 개념 {n}개 다시 보기", "voiceSwitched": "이 목소리로 읽어 드릴게요.",
        "oxTrue": "O", "oxFalse": "X",
    },
}

# Narration phrases. {..} placeholders are filled by build.py.
PHRASES = {
    "en": {
        "ordinals": ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth"],
        "step": "{o}. {name}",
        "volts": "{n} volts", "range": "{a} to {b}", "page": "page {n}",
        "vsIntro": "{L} versus {R}.", "vsSide": "{side}: {text}.", "win": "{W}: {winText}.",
        "hook": "Remember it like this. ", "terms": "Use these exact terms. ", "ex": "Example from the notes. ",
        "def": "Definition. {term}. ", "percent": " percent",
        "tri": ["{p} and {o}.", "{o} and {x}.", "So, {p} and {x}."],
        "intro": "{name}. {sub} {n} concepts, one at a time.",
        "outro": "That's {name}. Nice work. Ready for a quick memory check?",
        "listEnd": "Replay done. Let's re-check the concepts you just saw.",
        "ok": "Correct!", "oxO": "Not quite. The answer is true.", "oxX": "Not quite. The answer is false.",
        "resWrong": "Here are your results. Let's replay the concepts you missed.", "resPerfect": "Here are your results. Perfect!",
        "sample": "Hi. I'll walk you through each concept, one at a time.",
        "wrongPrefix": "Not quite. The answer is ", "oxSuffix": " True or false?",
    },
    "ko": {
        "ordinals": ["첫째", "둘째", "셋째", "넷째", "다섯째", "여섯째", "일곱째", "여덟째", "아홉째", "열째"],
        "step": "{o}, {name}",
        "volts": "{n}볼트", "range": "{a}에서 {b}", "page": "{n}쪽",
        "topicParticle": ["은", "는"], "subjectParticle": ["이", "가"],
        "vsIntro": "{L} 대 {R}.", "vsSide": "{side_topic} {text}.", "win": "{W_subject} {winText}.",
        "hook": "이렇게 기억하세요. ", "terms": "답안에는 이 용어로. ", "ex": "노트 속 예. ",
        "def": "노트 정의. {term}. ", "percent": "퍼센트",
        "tri": ["{p}, {o}.", "{o}, {x}.", "그러면 {p}, {x}."],
        "intro": "{name}. {sub} 개념 {n}개를 차례로 보여 드릴게요.",
        "outro": "{name}, 끝. 수고했어요. 이제 기억 확인 문제로 넘어가 볼까요?",
        "listEnd": "다시 보기 끝. 방금 본 개념을 다시 확인해 볼까요?",
        "ok": "정답!", "oxO": "아쉬워요. 정답은 오.", "oxX": "아쉬워요. 정답은 엑스.",
        "resWrong": "결과가 나왔어요. 틀린 개념만 다시 보여 드릴게요.", "resPerfect": "결과가 나왔어요. 완벽해요!",
        "sample": "안녕하세요. 지금부터 핵심 개념을 하나씩 들려 드릴게요.",
        "wrongPrefix": "아쉬워요. 정답은 ", "oxSuffix": " 오, 엑스로 답하세요.",
    },
}

# Symbols → spoken words, per language (applied after markup and parentheses are handled).
SYMBOLS = {
    "en": [(" → ", ", "), ("→", ", "), (" ↔ ", " and "), ("↔", " and "), (" ↑", " up"), ("↑", " up"), (" ↓", " down"), ("↓", " down"),
           (" = ", ", that is, "), (" vs ", " versus "), (" VS ", " versus "), ("✗", " no"), ("○", " yes"), (" & ", " and "), ("&", " and "),
           ("cf.", "compare"), ("e.g.", "for example"), ("i.e.", "that is")],
    "ko": [(" → ", ", "), ("→", ", "), (" ↔ ", ", "), ("↔", ", "), (" ↑", " 증가"), ("↑", " 증가"), (" ↓", " 감소"), ("↓", " 감소"),
           (" = ", ", 즉 "), (" vs ", " 대 "), ("VS", "대"), ("✗", " 아님"), ("○", " 맞음"), (" & ", ", "), ("&", ", "),
           ("cf.", "참고로")],
}
# Used for a language without a pack, after the course's own "symbols": only meaning-free punctuation.
# Symbols that carry meaning (↑ ↓ = ✗ ○ vs) are left in place so the narration lint flags them until the
# course gives them words in "symbols".
NEUTRAL_SYMBOLS = [(" → ", ", "), ("→", ", "), (" ↔ ", ", "), ("↔", ", "), (" & ", ", "), ("&", ", ")]

# Shared by every language
COMMON_SYMBOLS = [("**", ""), ("…", ""), ("...", ""), ("①", ""), ("②", ""), ("③", ""), ("④", ""),
                  (" · ", ", "), ("·", ", "), (" / ", ", "), ("/", ", "), (" + ", ", "), ("+", ", "), ("~", "")]

# Scripts where Latin-only glosses in parentheses should be dropped from narration
NON_LATIN = {"ko", "ja", "zh", "ru", "ar", "hi", "th", "he", "el", "uk"}


def pack(lang):
    """(ui, phrases, symbols, has_pack). Without a pack: English strings as a template, neutral symbols."""
    base = lang.split("-")[0]
    if base in UI:
        return dict(UI[base]), dict(PHRASES[base]), list(SYMBOLS[base]), True
    return dict(UI["en"]), dict(PHRASES["en"]), list(NEUTRAL_SYMBOLS), False
