import google.generativeai as genai
import os

# IMPORTANT: Replace "YOUR_API_KEY" with your actual Google AI API key
# For better security, load it from an environment variable.
# os.environ['GOOGLE_API_KEY'] = 'YOUR_API_KEY'
# genai.configure(api_key=os.environ['GOOGLE_API_KEY'])
genai.configure(api_key="YOUR_API_KEY")


def generate_summary(table1_data: list, table2_data: list, gl_account: str):
    """
    Generates a financial summary using the Gemini Pro model.
    """
    try:
        model = genai.GenerativeModel('gemini-pro')
        
        # Create a more structured prompt for better analysis
        prompt = f"""
        Analyze the following financial data for G/L Account {gl_account} and provide a concise summary with actionable insights.

        **Data Table 1: Balances by Ageing Bracket**
        This table shows the total amount distributed across different ageing periods.
        {table1_data}

        **Data Table 2: Balances by Division**
        This table shows the total amount distributed across different company divisions.
        {table2_data}

        **Your Task:**
        1.  **Overall Summary:** Briefly describe the financial situation for this G/L account.
        2.  **Ageing Analysis:** Point out any significant amounts in older ageing brackets (e.g., >1 year), as these could represent risks.
        3.  **Division Analysis:** Highlight the divisions that hold the largest amounts. Is the amount concentrated or widely distributed?
        4.  **Key Actionable Points:** Provide 2-3 bullet points on what requires immediate attention based on your analysis.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Could not generate AI summary. Error: {e}"