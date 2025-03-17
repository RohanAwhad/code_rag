# How to run

1. Start up postgres db using "docker compose up -d"
2. Install deps: `uv sync`
3. Add the following alias to your `.rc` file:
    ```bash
    alias code_rag="/Users/rohan/1_Porn/sundai_club/az_chapter/2025/mar_16_code_rag/.venv/bin/python /Users/rohan/1_Porn/sundai_club/az_chapter/2025/mar_16_code_rag/main.py \$(pwd)"
    ```
4. Head into any of your project and run `code_rag`.

This will start the rag server, and then you can use it in your dingllm. I have a fork maintained here: https://github.com/RohanAwhad/dingllm.nvim

Here's what you will need to add to your `init.lua` file:
```lua
local function anthropic_generate_with_context()
    dingllm.invoke_llm_and_stream_into_editor({
        url = "https://api.anthropic.com/v1/messages",
        model = "claude-3-7-sonnet-20250219",
        api_key_name = "ANTHROPIC_API_KEY",
        system_prompt = generation_system_prompt,
        replace = false,
        build_context = true,
    }, dingllm.make_anthropic_spec_curl_args, dingllm.handle_anthropic_spec_data)
end

vim.keymap.set({ "n", "v" }, "<leader>ic", anthropic_generate_with_context, { desc = "llm anthropic generate" })
```
