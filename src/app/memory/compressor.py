from langchain_core.prompts import ChatPromptTemplate


class MemoryCompressor:
    def __init__(self, model, summarizer_prompt: str, max_points: int):
        self.model = model
        self.max_points = max_points
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", summarizer_prompt),
                (
                    "human",
                    "Existing summary:\n{memory_summary}\n\n"
                    "New exchange:\nUser: {user_input}\nAction: {action}\nAssistant: {assistant_output}\nMemory note: {memory_note}\n\n"
                    "Return at most {max_points} bullets.",
                ),
            ]
        )

    def compress(
        self,
        memory_summary: str,
        user_input: str,
        action: str,
        assistant_output: str,
        memory_note: str = "",
    ) -> str:
        runnable = self.prompt | self.model
        response = runnable.invoke(
            {
                "memory_summary": memory_summary or "(none)",
                "user_input": user_input,
                "action": action,
                "assistant_output": assistant_output,
                "memory_note": memory_note or "(none)",
                "max_points": self.max_points,
            }
        )
        return str(response.content).strip()
