"""Реестр систем: все запускаются одним раннером через интерфейс harness.core.System."""


def get_system(name: str, **kwargs):
    if name == "b1":
        from .b1 import B1
        return B1()
    if name == "llm":
        from .llm_extract import LLMExtract
        return LLMExtract(**kwargs)
    raise SystemExit(f"неизвестная система: {name} (есть: b1, llm)")
