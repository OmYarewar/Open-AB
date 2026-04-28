from playwright.sync_api import sync_playwright

def browser_action(action: str, url: str = None, selector: str = None, text: str = None) -> str:
    """Perform a web browser action using Playwright to bypass paid APIs.
    Valid actions:
      - 'goto': Navigate to url. Returns page content snippet.
      - 'click': Click element at selector.
      - 'type': Type text into element at selector.
      - 'extract': Extract text content from element at selector.
    Note: For simplicity, this launches a new browser instance per action, which is slow but isolated.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            if action == 'goto':
                if not url: return "Error: 'url' is required for goto."
                page.goto(url)
                page.wait_for_load_state('networkidle')
                content = page.content()
                browser.close()
                return content[:5000] # return first 5k chars to avoid blowing up context

            elif action == 'click':
                if not url or not selector: return "Error: 'url' and 'selector' required."
                page.goto(url)
                page.click(selector)
                page.wait_for_load_state('networkidle')
                content = page.content()
                browser.close()
                return f"Clicked {selector}. New page snippet: {content[:1000]}"

            elif action == 'type':
                if not url or not selector or not text: return "Error: 'url', 'selector', 'text' required."
                page.goto(url)
                page.fill(selector, text)
                browser.close()
                return f"Typed '{text}' into {selector}."

            elif action == 'extract':
                if not url or not selector: return "Error: 'url' and 'selector' required."
                page.goto(url)
                content = page.locator(selector).text_content()
                browser.close()
                return content or "No content found."

            else:
                browser.close()
                return f"Error: Unknown action '{action}'"
    except Exception as e:
        return f"Error executing browser action: {e}"
