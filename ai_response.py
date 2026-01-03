from llama_cpp import Llama
import os
import types
import inspect
import re
from db_handler import lookup_acronym

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "ggml-model.bin")

if not os.path.isfile(MODEL_PATH):
    raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Download a ggml model and put it in the models/ folder.")

# Initialize the Llama client
llm = Llama(model_path=MODEL_PATH)

def extract_acronym(text: str):
    """Try several patterns to extract an acronym from a natural-language question."""
    text = text.strip()

    # fallback first: if the whole input is a single word of letters, treat as acronym
    if re.fullmatch(r"[A-Za-z]{1,6}", text):
        return text.upper()

    # bracketed form: [MVP] or (MVP)
    m = re.search(r"[\[\(]([A-Za-z]{1,6})[\]\)]", text)
    if m:
        return m.group(1).upper()

    # common question starters: "what is", "do you know what", etc.
    m = re.search(r"(?:what(?:'s| is)?|do you know what|do you know|define|explain)\s+(?:the\s+)?\[?([A-Za-z]{2,6})\]?(?:\s|$|\?)", text, re.IGNORECASE)
    if m:
        return m.group(1).upper()

    # pattern: "X means" or "X means?" or "X stands for"
    m = re.search(r"\b([A-Za-z]{2,6})\b(?=\s+(?:means|is|stands for|stand for|meaning))", text, re.IGNORECASE)
    if m:
        return m.group(1).upper()

    # prefer an all-caps token (common acronym form) — only 2+ letters to avoid articles
    m = re.search(r"\b([A-Z]{2,6})\b", text)
    if m:
        return m.group(1).upper()

    return None

def get_ai_response(user_input: str):
    """
    Accepts a plain string (from the GUI) and returns an AI-generated reply string.
    Handles natural-language queries asking about an acronym.
    Returns an informative error string for non-text or if no acronym detected.
    """
    try:
        if not isinstance(user_input, str):
            return "⚠️ Input error: expected text (e.g. 'what is mvp')."

        text = user_input.strip()
        if not text:
            return ""

        acronym = extract_acronym(text)
        if not acronym:
            return "⚠️ I couldn't detect an acronym in that question. Try 'what is MVP'?'."

        # Try to look up acronym in DB (lookup_acronym returns a dict or None)
        db_result = lookup_acronym(acronym)
        if db_result and db_result.get("meaning"):
            meaning_text = (db_result.get("meaning") or "").strip()
            extras = []
            teams = (db_result.get("teams") or "").strip()
            additional = (db_result.get("additionalMeaning") or "").strip()
            project = (db_result.get("project") or "").strip()
            notes = (db_result.get("notes") or "").strip()
            
            if teams:
                extras.append(f"👥 Used by: {teams}")
            if additional:
                extras.append(f"🧠 Other meanings: {additional}")
            if project:
                extras.append(f"📁 Related projects: {project}")
            if notes:
                extras.append(f"📝 Notes: {notes}")
            suffix = ("\n" + "\n".join(extras)) if extras else ""

            ai_reply = generate_ai_response(user_input.strip())
            return ai_reply
# Fallback to LLM if not found in DB
        prompt = f"What could '{acronym}' mean in a tech context?"
        ai_reply = generate_ai_response(prompt)
        if ai_reply:
            return f"🤔 I couldn't find '{acronym}' in my knowledge base.\n\nHere's my best guess:\n\n{ai_reply}"
        return f"I'm sorry, I don't know what '{acronym}' stands for."
    except Exception as e:
        return f"⚠️ AI error: {e}"
    
def generate_ai_response(prompt, max_tokens=200, stop=None):
    """
    Call the Llama client with multiple possible call signatures,
    consume streaming generators, and normalize returned text.
    """
    try:
        resp = None

        def safe_call(func, /, **kwargs):
            # prefer named-args, fall back to positional based on signature
            try:
                return func(**{k: v for k, v in kwargs.items() if v is not None})
            except TypeError:
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                pos = []
                if 'prompt' in params or 'prompts' in params or len(params) > 0:
                    pos.append(kwargs.get('prompt'))
                if 'max_tokens' in params:
                    pos.append(kwargs.get('max_tokens'))
                if 'stop' in params:
                    pos.append(kwargs.get('stop'))
                pos = [p for p in pos if p is not None]
                return func(*pos)

        if hasattr(llm, "create"):
            try:
                resp = safe_call(llm.create, prompt=prompt, max_tokens=max_tokens, stop=stop)
            except Exception:
                resp = safe_call(llm.create, prompt=prompt, max_tokens=max_tokens)
        elif hasattr(llm, "generate"):
            try:
                resp = safe_call(llm.generate, prompt=prompt, max_tokens=max_tokens, stop=stop)
            except Exception:
                try:
                    resp = safe_call(llm.generate, [prompt], max_tokens=max_tokens, stop=stop)
                except Exception:
                    resp = safe_call(llm.generate, prompt=prompt, max_tokens=max_tokens)
        elif callable(llm):
            try:
                resp = safe_call(llm, prompt=prompt, max_tokens=max_tokens, stop=stop)
            except Exception:
                resp = safe_call(llm, prompt=prompt, max_tokens=max_tokens)
        else:
            return "⚠️ AI error: incompatible llama-cpp-python API"

        # consume generator/streaming responses
        if isinstance(resp, types.GeneratorType) or (hasattr(resp, "__iter__") and not isinstance(resp, (str, bytes, dict, list, tuple))):
            parts = []
            for chunk in resp:
                if isinstance(chunk, dict):
                    parts.append(chunk.get("text") or chunk.get("content") or chunk.get("token") or "")
                else:
                    parts.append(getattr(chunk, "text", None) or getattr(chunk, "content", None) or str(chunk))
            combined = "".join(filter(None, map(str, parts))).strip()
            if combined:
                return combined

        # dict-like response
        if isinstance(resp, dict):
            choices = resp.get("choices") or []
            if choices:
                first = choices[0]
                if isinstance(first, dict):
                    return (first.get("text") or first.get("content") or "").strip()
            if "text" in resp:
                return str(resp.get("text", "")).strip()
            return ""

        # object-like responses with .choices
        choices = getattr(resp, "choices", None)
        if choices and len(choices) > 0:
            first = choices[0]
            return (getattr(first, "text", None) or getattr(first, "content", None) or "").strip()

        # some versions expose .generations
        gens = getattr(resp, "generations", None)
        if gens:
            try:
                candidate = gens[0][0]
                return (getattr(candidate, "text", None) or "").strip()
            except Exception:
                pass

        if resp is not None:
            print(f"⚠️ Warning: Unexpected response format: {type(resp)}")
            return str(resp).strip()
        return ""
    except Exception as e:
        return f"⚠️ AI error: {e}"

