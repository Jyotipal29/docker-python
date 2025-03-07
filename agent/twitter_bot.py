from typing import Any, Dict, List
from langchain.tools import tool
from playwright.async_api import async_playwright
import asyncio
import uuid
from langchain.agents import initialize_agent
from langchain.agents import AgentExecutor, create_tool_calling_agent, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import MessagesPlaceholder
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import create_react_agent
from langchain.tools.render import format_tool_to_openai_function
from dotenv import load_dotenv

load_dotenv()

BROWSER_SESSIONS = {}
TWITTER_ACC_EMAIL_ID = "paljyoti0129@gmail.com"
TWITTER_ACC_PASSWORD = "jyotiPal@29"



# ✅ Browser Launcher (Async)
# @tool
# async def browser_launcher() -> str:
#     """Launches a browser and authenticates on Twitter/X."""
#     try:
#         print("launched the browser")
#         playwright = await async_playwright().start()
#         browser = await playwright.chromium.launch(headless=False)
#         context = await browser.new_context()
#         await context.add_cookies([{
#             "name": "auth_token",
#             "value": "1578e0e2398361364ebbdc48d574352a055b56d9",
#             "domain": ".x.com",
#             "path": "/",
#         }])
#         page = await context.new_page()
#         await page.goto("https://x.com", wait_until="domcontentloaded")
#         await asyncio.sleep(10)
        
#         session_id = str(uuid.uuid4())
#         BROWSER_SESSIONS[session_id] = page
        
#         return session_id
#     except Exception as e:
#         return f"browser_error:{str(e)}"



async def browser_launcher() -> str:
    """Launches a browser and authenticates on Twitter/X."""
    try:
        print("launched the browser")
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://x.com/login", wait_until="domcontentloaded")
        await asyncio.sleep(5)
        email_input = page.locator("input")
        await email_input.click()
        await email_input.fill(TWITTER_ACC_EMAIL_ID)
        await asyncio.sleep(2)
        next_btn = page.locator("button", has_text="Next")
        await next_btn.click()
        await asyncio.sleep(5)
        
        password_input = page.locator("input[name='password']")
        await password_input.fill(TWITTER_ACC_PASSWORD)
        await asyncio.sleep(2)
        
        login_button = page.locator('[data-testid="LoginForm_Footer_Container"] button', has_text="Log in")
        await login_button.click()

        
        await asyncio.sleep(10)
        
        session_id = str(uuid.uuid4())
        BROWSER_SESSIONS[session_id] = page
        
        return session_id
    except Exception as e:
        return f"browser_error:{str(e)}"

# ✅ Smart Scroller (Async)
async def smart_scroller(session_id: str) -> str:
    """Scrolls through the Twitter/X feed."""
    try:
        print("scrolling")

        page = BROWSER_SESSIONS.get(session_id)
        if not page:
            return "scroll_error: Invalid session ID"
          
        if page.is_closed():
            print("Error: Page is closed.")
            return "scroll_error: Page is closed"
          
        await page.wait_for_load_state("domcontentloaded")

        for _ in range(1):
            print("Scrolling...", page, "type", type(page))
            await page.evaluate("() => { window.scrollBy(0, window.innerHeight * 0.8); }")
          
            await asyncio.sleep(1.5)
            tweet_count = await page.locator('[data-testid="tweet"]').count()
           

        return f"scroll_success:{tweet_count}"
    except Exception as e:
        return f"scroll_error:{str(e)}"





      
@tool
async def collect_tweets_from_dom(session_id: str) -> str:
    """Collects tweets from current view"""
    try:

        page = BROWSER_SESSIONS.get(session_id)
        if not page:
            return "like_error: Invalid session ID"

        tweets_arr = await page.locator('[data-testid="tweet"]').all()
        print('line 123', tweets_arr)
        return tweets_arr
    except Exception as e:
        return f"like_error:{str(e)}"

# ✅ Tweet Collector (Async)
@tool
async def tweet_collector(session_id: str, limit: int = 1) -> List[str]:
    """Collects tweet IDs from the feed, up to a specified limit."""
    try:
        print("collectng tweets")

        page = BROWSER_SESSIONS.get(session_id)
        if not page:
            return ["error: Invalid session ID"]

        collected_tweets = []

        while len(collected_tweets) < limit:
            tweets = page.locator('article[data-testid="tweet"]')
            count = await tweets.count()
            print(f"Total tweets found: {count}")

            for i in range(count):
                if len(collected_tweets) >= limit:
                    break

                tweet = tweets.nth(i)
                # link_locator = tweet.locator('a[href*="status"]')
                username_container = tweet.locator('div[data-testid="User-Name"]')
                link_locator = username_container.locator('a[href*="status"]')
                
                if await link_locator.count() == 0:
                    continue

                await link_locator.wait_for(state="visible", timeout=5000)
                link_href = await link_locator.get_attribute('href')

                if link_href and 'status' in link_href:
                    collected_tweets.append(link_href)

            if len(collected_tweets) < limit:
                await smart_scroller(session_id)

        return collected_tweets
    except Exception as e:
        return [f"collector_error: {str(e)}"]



def convert_shorthand_to_decimal(shorthand: str) -> int:
    """
    Convert a shorthand notation like '4M' or '3K' into its decimal equivalent.

    Parameters:
    shorthand (str): The shorthand string to convert (e.g., '4M', '3K').

    Returns:
    int: The decimal equivalent of the shorthand notation.
    """
    shorthand = shorthand.upper().strip().replace(',', '')
    if shorthand.endswith('M'):
        return int(float(shorthand[:-1]) * 1_000_000)
    elif shorthand.endswith('K'):
        return int(float(shorthand[:-1]) * 1_000)
    else:
        return int(shorthand)
    


async def generate_qoute(tweet_text:str)->str:
    """Generate a comment based on the tweet content."""
    try:
        model = ChatOpenAI(
            api_key="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",
            base_url="https://api.groq.com/openai/v1/",
            model="llama3-70b-8192",
            temperature=0
        )

      

        prompt_text = f"""
            Tweet to quote: {tweet_text}

            Task: Generate a concise, impactful quote that adds unique value when resharing this tweet.

            Requirements:
            1. Length: Strictly under 220 characters
            2. Style:
            - Professional and articulate
            - Zero emojis or hashtags
            - No abbreviations or informal language
            - Perfect grammar and spelling
            - Clear and direct tone

            Content Guidelines:
            - Add unique insights or perspectives not present in the original tweet
            - Highlight key implications or applications
            - Connect ideas to broader tech trends or practical uses
            - Express your professional opinion or expertise
            - Ask thought-provoking questions when relevant

            Quote Format:
            - Start with a strong hook or insight
            - Focus on ONE key point
            - End with impact
            - Avoid generic phrases like "Great thread!" or "Important topic!"

            ULTRA-CRITICAL OUTPUT INSTRUCTIONS:
            - Your entire response must ONLY contain the quote itself
            - DO NOT include ANY preface text like "Here's a quote:" or "Generated quote:"
            - DO NOT include ANY explanation, introduction, or conclusion
            - DO NOT start with phrases like "Here is" or "Quote:"
            - DO NOT include any quotation marks at beginning or end
            - DO NOT wrap the response in any formatting
            - The FIRST and LAST character of your response must be part of the actual quote
            - Total response must be under 220 characters

            Examples of CORRECTLY FORMATTED responses:
            The revolutionary approach to transformer architecture could reduce training costs by 30% while maintaining accuracy
            Fascinating research on attention mechanisms - the implications for model efficiency are groundbreaking
            This compelling case for edge AI reshaping mobile computing challenges our assumptions about cloud dependency

            Examples of INCORRECT responses:
            ❌ "Here's a quote: This research could revolutionize..."
            ❌ "Generated quote: The implications for edge computing..."
            ❌ "Quote: A crucial perspective on AI safety..."

            YOUR ENTIRE RESPONSE SHOULD BE JUST THE QUOTE TEXT AND NOTHING ELSE.
        """


        comment = model.invoke(prompt_text).content.strip().strip('"')
        
       
        print('Generated quote:', comment)
        print('Character count:', len(comment))
        
        return comment
    except Exception as e:
        return f"error: {str(e)}"
    

    

async def generate_comment(tweet_text: str) -> str:
    """Generate an engaging comment response to a tweet."""
    try:
        model = ChatOpenAI(
            api_key="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",
            base_url="https://api.groq.com/openai/v1/",
            model="llama3-70b-8192",
            temperature=0
        )

        prompt_text = f"""
        Tweet to respond to: {tweet_text}

        Task: Create an engaging, conversational comment that naturally flows as a response to this tweet.

        Response Requirements:
        1. Length: Strictly under 220 characters
        2. Tone:
           - Friendly and approachable
           - Subtly humorous where appropriate
           - Professional yet conversational
           - Always positive and constructive

        Content Guidelines:
        - Respond directly to the tweet's main point
        - Add a unique perspective or insight
        - Share relevant personal experience if applicable
        - Ask thoughtful questions that advance the discussion
        - Use natural, conversational language
        - Avoid generic responses like "Great point!" or "Interesting thread!"

        Strict Rules:
        - NO hashtags
        - NO emojis
        - NO spelling mistakes
        - NO grammar errors
        - NO quotation marks at start or end
        - NO unnecessary formatting

        Examples of Good Comments:
        ✓ Fascinating insight! Have you considered how this could impact smaller development teams? The productivity gains could be game-changing.
        ✓ Your point about latency issues resonates strongly. We faced similar challenges and found edge computing to be the perfect solution.
        ✓ This reminds me of the parallel processing debate from last year. The industry has come so far since then.

        Examples of Bad Comments:
        ❌ "Great thread! 🔥 #AI #Tech"
        ❌ "This is so cool! Following u for more content!"
        ❌ "Wow, never thought about this before..."

        Generate a natural, engaging response that could start a meaningful conversation. Return only the plain comment text with no quotes or special formatting.
        """

        comment = model.invoke(prompt_text).content.strip().strip('"')
        print('Generated comment:', comment)
        print('Character count:', len(comment))
        
        return comment
    except Exception as e:
        return f"error: {str(e)}"


      
@tool
async def navigate_to_single_tweet(session_id: str, tweet_link: str) -> str:
    """Navigates to single tweet"""
    try:
        print("Navigate to single tweet starts")

        page = BROWSER_SESSIONS.get(session_id)
        if not page:
            return "error: Invalid session ID"
        if 'status' in tweet_link:
          tweet_url = f"https://x.com{tweet_link}"
          await page.goto(tweet_url, wait_until="domcontentloaded")
          await asyncio.sleep(5)
        else:
          print(f'Something wrong with the link: {tweet_link}')
          
        return 'navigated successfully'
    except Exception as e:
        return f"error: {str(e)}"
      

      



@tool
async def read_and_analyze_tweet(session_id: str) -> str:
    """Reads the tweet content and analyzes if it's worth liking, commenting, or retweeting."""
    try:
        page = BROWSER_SESSIONS.get(session_id)
        if not page:
            return "error: Invalid session ID"
        
        print('Reading and analyzing tweet')
          
        # PART 1: READ THE TWEET
        primary_column = page.locator('[data-testid="primaryColumn"]')
        await primary_column.wait_for(state="visible", timeout=5000)

        primary_tweet = primary_column.locator('[data-testid="cellInnerDiv"]').nth(0)
        await primary_tweet.wait_for(state="visible", timeout=5000)

        # Check if it's our own tweet
        tweet_posted_by = primary_tweet.locator('[data-testid="User-Name"]').nth(0)
        tweet_posted_by_username = await tweet_posted_by.inner_html()
        if '@llm_guruji' in tweet_posted_by_username:
            return "skipped: own tweet"

        # Get tweet text
        tweet_text_block = primary_tweet.locator('[data-testid="tweetText"]').nth(0)
        tweet_text = await tweet_text_block.inner_text()
        print('Tweet content:', tweet_text)
        
        # Get engagement metrics
        try:
            # Like count
            tweet_like_count_container = primary_tweet.locator('[data-testid="like"] [data-testid="app-text-transition-container"]')
            tweet_like_count = await tweet_like_count_container.inner_text()
            formatted_like_count = convert_shorthand_to_decimal(tweet_like_count)
            
            # Comment count
            tweet_reply_count_container = primary_tweet.locator('[data-testid="reply"] [data-testid="app-text-transition-container"]')
            tweet_reply_count = await tweet_reply_count_container.inner_text()
            formatted_reply_count = convert_shorthand_to_decimal(tweet_reply_count)
          
            # Retweet count
            tweet_retweet_count_container = primary_tweet.locator('[data-testid="retweet"] [data-testid="app-text-transition-container"]')
            tweet_retweet_count = await tweet_retweet_count_container.inner_text()
            formatted_retweet_count = convert_shorthand_to_decimal(tweet_retweet_count)

            # Impression count
            impression_value = await primary_tweet.locator('[data-testid="app-text-transition-container"]').nth(0).inner_text()
            formatted_impression_count = convert_shorthand_to_decimal(impression_value)
            
            print(f'Metrics: {formatted_like_count} likes, {formatted_reply_count} replies, {formatted_retweet_count} retweets')
        except Exception as metric_error:
            print(f"Error getting metrics: {str(metric_error)}")
            formatted_like_count = 0
            formatted_reply_count = 0
            formatted_retweet_count = 0
            formatted_impression_count = 0

        # PART 2: ANALYZE THE TWEET
        model = ChatOpenAI(
            api_key="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",
            base_url="https://api.groq.com/openai/v1/",
            model="llama3-70b-8192",
            temperature=0
        )

        prompt_text = f"""
        Analyze the following tweet:
        
        Tweet text: {tweet_text}
        Like count: {formatted_like_count}
        Reply count: {formatted_reply_count}
        Retweet count: {formatted_retweet_count}
        Impression count: {formatted_impression_count}
        
        Step 1: Analyze the following text to determine:
        Step 1.1: Does it discuss technology-related topics such as AI, AI agents, AI in space, LLMs, LLM models, machine learning, NLP, or overall tech in general?
        Step 1.2: Does it maintain a positive tone and refrain from spreading hate?

        And if both are true, is_tech_related should be True, else False.
            
        Step 2: Evaluate the following tweet to decide if it should be liked:
        Consider if the tweet discusses deep tech topics and maintains a positive tone.
        If this criterion is met, should_like should be True; otherwise, False.

        Step 3: Evaluate the following tweet to decide if it should be reposted:
        Consider:
        - If the tweet aligns with tech interests
        - If it offers valuable information worth sharing
        - If it has good engagement metrics (Impression count and  Retweet count)
        - If the information is credible
        
        If these criteria are met, should_retweet should be True; otherwise, False.

        Step 4: Evaluate the following tweet to decide if it warrants a comment:
        Consider if:
        - The tweet invites discussion
        - Adding a comment could foster meaningful discussion
        - You have valuable insights to contribute
        - A comment would be constructive
        
        If these criteria are met, should_comment should be True; otherwise, False.
        
        Return your analysis in exactly this format:
        "tweet_text:{tweet_text} ,is_tech_related: [True/False], should_like: [True/False], should_retweet: [True/False], should_comment: [True/False]"
        """

        tweet_analysis = model.invoke(prompt_text).content.strip()
        print("Analysis result:", tweet_analysis)
        return tweet_analysis
    
    except Exception as e:
        print(f"Read/analyze error: {str(e)}")
        return f"tweet_text:{tweet_text} ,is_tech_related: False, should_like: False, should_retweet: False, should_comment: False"







async def retry_async(func, max_retries=3, delay_in_sec=60, *args, **kwargs):
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            print('some error', e)
            if attempt == max_retries - 1:
                return f"error: {str(e)}"
            print(f"Retrying in {delay_in_sec} seconds...")
            await asyncio.sleep(delay_in_sec)

@tool
async def like_single_tweet(session_id: str) -> str:
    """Likes a tweet for the given session.
    
    Args:
        session_id (str): The session identifier for the Twitter browser instance.
    
    Returns:
        str: "tweet_liked" if successful, or an error message if not.
    """
    try:
        async def _like():
            page = BROWSER_SESSIONS.get(session_id)
            if not page:
                return "error: Invalid session ID"
            
            primary_column = page.locator('[data-testid="primaryColumn"]')
            await primary_column.wait_for(state="visible", timeout=5000)

            primary_tweet = primary_column.locator('[data-testid="cellInnerDiv"]').nth(0)
            await primary_tweet.wait_for(state="visible", timeout=5000)

            tweet_posted_by = primary_tweet.locator('[data-testid="User-Name"]').nth(0)
            tweet_posted_by_username = await tweet_posted_by.inner_html()

            if '@llm_guruji' in tweet_posted_by_username:
                return "skipped: own tweet"

            like_button = primary_tweet.locator('[data-testid="like"]')
            await like_button.click()
            await asyncio.sleep(1)

            return "tweet_liked"
        
        return await retry_async(_like)
    except Exception as e:
        return f"error: {str(e)}"

@tool
async def repost_single_tweet(session_id: str,tweet_text) -> str:
    """Repost the tweet."""
    try:
        async def _repost():
            
            page = BROWSER_SESSIONS.get(session_id)
            if not page:
                return "error: Invalid session ID"
            
            primary_column = page.locator('[data-testid="primaryColumn"]')
            await primary_column.wait_for(state="visible", timeout=5000)

            primary_tweet = primary_column.locator('[data-testid="cellInnerDiv"]').nth(0)
            await primary_tweet.wait_for(state="visible", timeout=5000)
            
            comment = await generate_qoute(tweet_text)
            
            retweet_button = primary_tweet.locator('[data-testid="retweet"]')
            await retweet_button.click()
            await asyncio.sleep(1)

            repost_popup = page.locator('[data-testid="Dropdown"]')
            quote_btn = repost_popup.locator('a')
            await quote_btn.nth(0).click()
            await asyncio.sleep(2)
            
            repost_quote_modal = page.locator('div[aria-labelledby="modal-header"]')
            if await repost_quote_modal.is_visible():
              comment_box = page.locator('div[aria-labelledby="modal-header"] div[data-testid="tweetTextarea_0"]')
              
              print(comment,"in 931")
              await comment_box.fill(comment)
              await asyncio.sleep(1)
              
              post_quote_reply_button = page.locator('[data-testid="tweetButton"]')
              await post_quote_reply_button.click()
              await asyncio.sleep(2)
              
              print("tweet reply quote completed")
            else:
              print("error: repost_quote_modal not opened")
          
            await asyncio.sleep(2)
            
            return "tweet repost completed"
        
        return await retry_async(_repost)
    except Exception as e:
        return f"error: {str(e)}"

@tool
async def reply_single_tweet(session_id: str,tweet_text) -> str:
    """Replies to a tweet."""
    try:
        async def _reply():
        
            page = BROWSER_SESSIONS.get(session_id)
            if not page:
                return "error: Invalid session ID"
            
            primary_column = page.locator('[data-testid="primaryColumn"]')
            await primary_column.wait_for(state="visible", timeout=5000)

            primary_tweet = primary_column.locator('[data-testid="cellInnerDiv"]').nth(0)
            await primary_tweet.wait_for(state="visible", timeout=5000)
            
            comment = await generate_comment(tweet_text)
            
            reply_button = primary_tweet.locator('button[data-testid="reply"]')
            await reply_button.click()
            await asyncio.sleep(3)

            reply_modal = page.locator('div[aria-labelledby="modal-header"]')
            if await reply_modal.is_visible():
                comment_box = page.locator('div[aria-labelledby="modal-header"] div[data-testid="tweetTextarea_0"]')
                
                print(comment,"in 971")
                await comment_box.fill(comment)
                await asyncio.sleep(1)
                
                post_reply_button = page.locator('[data-testid="tweetButton"]')
                await post_reply_button.click()
                await asyncio.sleep(2)
                
                return "tweet reply completed"
            else:
                return "error: reply modal not opened"
        
        return await retry_async(_reply)
    except Exception as e:
        return f"error: {str(e)}"

@tool
async def navigate_back_to_twitter(session_id: str) -> str:
    """Navigate to Twitter homepage."""
    try:
        async def _navigate():
            page = BROWSER_SESSIONS.get(session_id)
            if not page:
                return "error: Invalid session ID"
            
            await page.goto("https://x.com", wait_until="domcontentloaded")
            await asyncio.sleep(10)

            return "navigated"
        
        return await retry_async(_navigate)
    except Exception as e:
        return f"error: {str(e)}"
  


# ✅ List of Tools
tools = [
    tweet_collector,
    navigate_to_single_tweet,
    read_and_analyze_tweet,
    
    like_single_tweet,
    repost_single_tweet,
    reply_single_tweet,
    navigate_back_to_twitter
]



prompt_text = f"""

Your task is to intelligently browse Twitter/X, identify high-engagement tweets, and interact with them using the available tools. Follow this structured approach:

 Step 1: Say hello
   
 Step 2: Collect the the tweet links
  - Use the `tweet_collector` tool to extract a list of tweet IDs and store the response in `collected_tweets`
   
 Step 3: Loop over the collected_tweets
  - Follow the below steps in each iteration
  Step 3.1 : Use navigate_to_single_tweet tool and pass session_id and pass the loop control variable from collected_tweets loop
  Step 3.2 : Call `read_and_analyze_tweet` tool with session_id. Store the response in `tweet_analysis`.And continue to step 3.3
  Step 3.3 : If `tweet_analysis` have should_like: True and is_tech_related: True then only invoke like_single_tweet tool and pass session_id to like the tweet and wait for response
  Step 3.4 : If `tweet_analysis` have should_retweet: True and is_tech_related: True then only invoke repost_single_tweet tool and pass session_id and tweet_text from `tweet_analysis` to repost the tweet
  Step 3.5 : If `tweet_analysis` have should_comment: True and is_tech_related: True then only invoke reply_single_tweet tool and pass session_id and tweet_text from `tweet_analysis` to reply on the tweet

 Step 4: Go back to twitter homepage using navigate_back_to_twitter tool

 Step 5: Repeat from Step 2 to Step 4 continuously


🔹 **Goal:** Maximize meaningful interactions while ensuring engagement appears natural and human-like.  

🚀 **Now execute the engagement process autonomously using the provided tools!**

"""


# Main entry point function to run the bot
async def run_bot_session(session_id=None):
    """Main entry point with a single asyncio.run()"""
    if not session_id:
        session_id = await browser_launcher()
    
    updated_prompt_text = f"(session_id: {session_id}) {prompt_text}"
    
    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(updated_prompt_text),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])

    llm = ChatOpenAI( 
        api_key="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",
        base_url="https://api.groq.com/openai/v1/",  
        model="llama3-70b-8192", 
        temperature=0
    )
    
    agent = create_openai_tools_agent(llm, tools, prompt)

    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True,
        max_iterations=50,
        handle_parsing_errors=True
    )

    return session_id, agent_executor


BOT_TASKS = {}  # Global variable to track running bot tasks

# async def main_bot_loop(session_id, agent_executor):
#     """Main bot loop that can be started and stopped"""
    
#     task_id = str(uuid.uuid4())
#     BOT_TASKS[task_id] = {
#         "session_id": session_id,
#         "running": True,
#         "start_time": None,
#     }
    
#     BOT_TASKS[task_id]["start_time"] = asyncio.get_event_loop().time()
    
#     while BOT_TASKS[task_id]["running"]:
#         try:
#             response = await agent_executor.ainvoke({"input": prompt_text})
#             print(response)
#         except Exception as e:
#             print("❌ Error:", str(e))
#             print('navigating to homepage')
#             page = BROWSER_SESSIONS.get(session_id)
#             if not page:
#                 print("error: Invalid session ID")
#                 break
            
#             try:
#                 await page.goto("https://x.com", wait_until="domcontentloaded")
#             except Exception as nav_error:
#                 print(f"Navigation error: {nav_error}")
            
#         if not BOT_TASKS[task_id]["running"]:
#             print(f"Bot task {task_id} stopped")
#             break
            
#         print('20 sec timer starts')
#         await asyncio.sleep(20)  # Wait before the next iteration
#         print('20 sec timer ends')
    
#     return task_id


# async def main_bot_loop(session_id, agent_executor):
#     """Main bot loop that can be started and stopped"""
    
#     task_id = str(uuid.uuid4())
#     BOT_TASKS[task_id] = {
#         "session_id": session_id,
#         "running": True,
#         "start_time": asyncio.get_event_loop().time(),
#     }
    
#     try:
#         while BOT_TASKS[task_id]["running"]:
#             try:
#                 # Check if browser session is still valid before invoking the agent
#                 page = BROWSER_SESSIONS.get(session_id)
#                 if not page or page.is_closed():
#                     print(f"Browser session {session_id} is no longer valid, stopping bot")
#                     BOT_TASKS[task_id]["running"] = False
#                     break
                
#                 response = await agent_executor.ainvoke({"input": prompt_text})
#                 print(response)
#             except asyncio.CancelledError:
#                 # Handle explicit cancellation
#                 print("Task was cancelled, stopping bot")
#                 BOT_TASKS[task_id]["running"] = False
#                 break
#             except Exception as e:
#                 print("❌ Error:", str(e))
#                 print('navigating to homepage')
                
#                 # Check if browser is still open
#                 page = BROWSER_SESSIONS.get(session_id)
#                 if not page or page.is_closed():
#                     print("Browser is closed, stopping bot")
#                     BOT_TASKS[task_id]["running"] = False
#                     break
                
#                 try:
#                     await page.goto("https://x.com", wait_until="domcontentloaded")
#                 except:
#                     # If navigation fails, browser might be gone
#                     BOT_TASKS[task_id]["running"] = False
#                     break
            
#             if not BOT_TASKS[task_id]["running"]:
#                 print(f"Bot task {task_id} stopped")
#                 break
                
#             print('20 sec timer starts')
#             # Use asyncio.sleep with cancellation check
#             try:
#                 await asyncio.sleep(20)  # Wait before the next iteration
#             except asyncio.CancelledError:
#                 print("Sleep cancelled, stopping bot")
#                 BOT_TASKS[task_id]["running"] = False
#                 break
#             print('20 sec timer ends')
#     finally:
#         # Always mark as not running when loop exits
#         if task_id in BOT_TASKS:
#             BOT_TASKS[task_id]["running"] = False
#         print(f"Bot loop for task {task_id} ended")
    
#     return task_id



async def main_bot_loop(session_id, agent_executor):
    """Main bot loop that can be started and stopped"""
    
    task_id = str(uuid.uuid4())
    BOT_TASKS[task_id] = {
        "session_id": session_id,
        "running": True,
        "start_time": asyncio.get_event_loop().time(),
    }
    
    try:
        while BOT_TASKS.get(task_id, {}).get("running", False):
            try:
                # Check if browser session is still valid before invoking the agent
                page = BROWSER_SESSIONS.get(session_id)
                if not page or page.is_closed():
                    print(f"Browser session {session_id} is no longer valid, stopping bot")
                    if task_id in BOT_TASKS:  # Check if still exists
                        BOT_TASKS[task_id]["running"] = False
                    break
                
                response = await agent_executor.ainvoke({"input": prompt_text})
                print(response)
            except asyncio.CancelledError:
                # Handle explicit cancellation
                print("Task was cancelled, stopping bot")
                break  # Just break the loop, don't modify BOT_TASKS
            except Exception as e:
                print("❌ Error:", str(e))
                print('navigating to homepage')
                
                # Check if browser is still open
                page = BROWSER_SESSIONS.get(session_id)
                if not page or page.is_closed():
                    print("Browser is closed, stopping bot")
                    break  # Just break the loop, don't modify BOT_TASKS
                
                try:
                    await page.goto("https://x.com", wait_until="domcontentloaded")
                except:
                    # If navigation fails, browser might be gone
                    break  # Just break the loop, don't modify BOT_TASKS
            
            if task_id not in BOT_TASKS or not BOT_TASKS[task_id]["running"]:
                print(f"Bot task {task_id} stopped")
                break
                
            print('20 sec timer starts')
            # Use asyncio.sleep with cancellation check
            try:
                await asyncio.sleep(20)  # Wait before the next iteration
            except asyncio.CancelledError:
                print("Sleep cancelled, stopping bot")
                break  # Just break the loop, don't modify BOT_TASKS
            print('20 sec timer ends')
    except Exception as e:
        print(f"Unhandled exception in main_bot_loop: {str(e)}")
    finally:
        # Always mark as not running when loop exits, if the task still exists
        print(f"Bot loop for task {task_id} ended")
        # Safely check if the task_id still exists in BOT_TASKS
        if task_id in BOT_TASKS:
            BOT_TASKS[task_id]["running"] = False
    
    return task_id




if __name__ == "__main__":
    if asyncio.get_event_loop().is_closed():
        asyncio.set_event_loop(asyncio.new_event_loop())

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())