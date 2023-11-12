---
layout: post
title:  "Tiny Collaborative Editor"
author: Ivan Bercovich
date:   2023-11-11 01:01:01 -0700
categories:
---

# Tiny Collaborative Editor #

I made a simple collaborative editor in preact, using firepad and firebase. Over the years, I've had many ideas for collaborative applications, most recently for collaborating with an LLM. Firepad is great but outdated and the sample code is not meant to be reactive. All dependencies are included via `<script>` tags. This is a great approach for prototyping small applications because it allows for fast debugging and virtually free deployment. Thanks to firebase, this application allows for authentication as well. 

[Fork here](https://github.com/ibercovich/firepad-preact) 

![](/assets/tiny-collaborative-editor.webp)

## Example LLM component

```javascript
import Config from "../config.js";

function LLM({ firepad }) {
  const [apiKey, setApiKey] = useState(
    localStorage.getItem("OpenAIapiKey") || ""
  );
  const [gptResponse, setGptResponse] = useState(null);
  const [loading, setLoading] = useState(null);
  const [model, setModel] = useState(Config.model);
  const [prompt, setPrompt] = useState(null);
  const [systemPrompt, setSystemPrompt] = useState(Config.sysPrompt);

  const doSomethingWithLLMs = () => {
    if (firepad) {
      // prompt will likely include part of the current document
      const _prompt = "some prompt =>" + firepad.getText();
      setPrompt(_prompt);
    }
  };

  useEffect(() => {
    if (prompt) {
      handleSubmit();
    }
  }, [prompt]);

  useEffect(() => {
    if (gptResponse) {
      // some combination of gptResponse and original document text
      const text =  gptResponse + firepad.getText()};
      firepad.setText(text);
    }
  }, [gptResponse]);

  const handleSubmit = async () => {
    setGptResponse("");
    setLoading(true);

    const response = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: model,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: prompt },
        ],
        temperature: 0.9,
      }),
    });

    const data = await response.json();
    setLoading(false);
    if (data.choices && data.choices.length > 0) {
      const message = data.choices[0].message.content;
      setGptResponse(message);
    } else {
      console.error("Error: GPT response does not contain choices.");
    }
  };

  const handleApiKeyChange = (event) => {
    localStorage.setItem("OpenAIapiKey", event.target.value);
    setApiKey(event.target.value);
  };

  return html` <div class="field has-addons">
    <div class="control">
      <input
        class="input is-small"
        type="text"
        value=${apiKey}
        onInput=${handleApiKeyChange}
        placeholder="OpenAI API key"
      />
    </div>
    <div class="control">
      <a
        onClick=${doSomethingWithLLMs}
        class="button is-info is-small ${loading ? " is-loading" : ""}"
        >Scopy</a
      >
    </div>
  </div>`;
}

export default LLM;
```

![](/assets/tiny-collaborative-editor-screenshot.png)