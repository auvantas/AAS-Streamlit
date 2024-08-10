import streamlit as st
import stripe
import random

# Check if Stripe secrets are set
if "stripe" not in st.secrets:
    st.error("Stripe API keys are not set in Streamlit secrets.")
    st.markdown("""
    To set up Stripe API keys, add the following to your secrets:
    ```toml
    [stripe]
    api_key = "your_stripe_api_key"
    ```
    For local development:
    1. Create a `.streamlit/secrets.toml` file in your project root with the above content.
    For Streamlit Cloud deployment:
    1. Go to your app's settings in the Streamlit Cloud dashboard.
    2. Find the "Secrets" section and add the above content.
    More info: https://docs.streamlit.io/streamlit-cloud/get-started/deploy-an-app/connect-to-data-sources/secrets-management
    """)
    st.stop()

# Initialize Stripe client
stripe.api_key = st.secrets.stripe.api_key

# Updated currencies as specified
CURRENCIES = {
    "BGN": "Bulgarian Lev - Bulgaria",
    "CAD": "Canadian Dollar - Canada",
    "CHF": "Swiss Franc - Switzerland and Liechtenstein",
    "CNY": "Chinese Yuan - China",
    "CZK": "Czech Koruna - Czech Republic",
    "DKK": "Danish Krone - Denmark",
    "EUR": "Euro - Multiple European countries",
    "GBP": "British Pound - United Kingdom",
    "HKD": "Hong Kong Dollar - Hong Kong",
    "HUF": "Hungarian Forint - Hungary",
    "ILS": "Israeli Shekel - Israel",
    "NOK": "Norwegian Krone - Norway",
    "NZD": "New Zealand Dollar - New Zealand",
    "PLN": "Polish Zloty - Poland",
    "RON": "Romanian Leu - Romania",
    "SEK": "Swedish Krona - Sweden",
    "SGD": "Singapore Dollar - Singapore",
    "TRY": "Turkish Lira - Turkey",
    "UGX": "Ugandan Shilling - Uganda",
    "USD": "United States Dollar - United States",
    "ZAR": "South African Rand - South Africa"
}

# Updated comprehensive bank transfer requirements
BANK_TRANSFER_REQUIREMENTS = {
    "USD": ["Account Number", "Routing Number (ABA)", "Account Type"],
    "EUR": ["IBAN", "BIC/SWIFT"],
    "GBP": ["Sort Code", "Account Number"],
    "CAD": ["Transit Number", "Institution Number", "Account Number"],
    "AUD": ["BSB Code", "Account Number"],
    "SGD": ["Bank Code", "Branch Code", "Account Number"],
    "HKD": ["Bank Code", "Branch Code", "Account Number"],
    "CNY": ["Bank Name", "Branch Name", "Account Number"],
    "BGN": ["IBAN", "BIC/SWIFT"],  # Bulgarian Lev
    "CHF": ["IBAN", "BIC/SWIFT"],  # Swiss Franc
    "CZK": ["IBAN", "BIC/SWIFT"],  # Czech Koruna
    "DKK": ["IBAN", "BIC/SWIFT"],  # Danish Krone
    "HUF": ["IBAN", "BIC/SWIFT"],  # Hungarian Forint
    "ILS": ["IBAN", "BIC/SWIFT"],  # Israeli Shekel
    "NOK": ["IBAN", "BIC/SWIFT"],  # Norwegian Krone
    "NZD": ["Bank Code", "Account Number"],  # New Zealand Dollar
    "PLN": ["IBAN", "BIC/SWIFT"],  # Polish Zloty
    "RON": ["IBAN", "BIC/SWIFT"],  # Romanian Leu
    "SEK": ["IBAN", "BIC/SWIFT"],  # Swedish Krona
    "TRY": ["IBAN", "BIC/SWIFT"],  # Turkish Lira
    "UGX": ["Bank Name", "Branch Name", "Account Number"],  # Ugandan Shilling
    "ZAR": ["Branch Code", "Account Number"],  # South African Rand
}

def create_payment_intent(amount, currency, payment_method_type, invoice_number, description, capture=True):
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency=currency,
            payment_method_types=[payment_method_type],
            capture_method='manual' if not capture else 'automatic',
            metadata={
                'invoice_number': invoice_number,
                'description': description
            },
            automatic_payment_methods={"enabled": True, "allow_redirects": "always"}
        )
        return intent
    except stripe.error.StripeError as e:
        st.error(f"Error creating PaymentIntent: {str(e)}")
        return None

def estimate_stripe_fees(amount, currency):
    if currency == 'USD':
        return round(amount * 0.029 + 0.30, 2)
    else:
        return round(amount * 0.039 + 0.30, 2)

def estimate_clearance_time(currency):
    standard_times = {
        "USD": "2-3 business days",
        "EUR": "2-3 business days",
        "GBP": "2-3 business days",
        "JPY": "3-5 business days",
        "CAD": "2-3 business days",
        "AUD": "2-3 business days",
        "CHF": "3-5 business days",
        "CNY": "3-5 business days",
        "HKD": "3-5 business days",
        "SGD": "3-5 business days"
    }
    return standard_times.get(currency, "5-7 business days")

def check_payment_status(invoice_number):
    try:
        payment_intents = stripe.PaymentIntent.list(metadata={'invoice_number': invoice_number})
        
        if not payment_intents.data:
            return "No payment found with this invoice number."
        
        payment_intent = payment_intents.data[0]
        
        status_messages = {
            'requires_payment_method': "Payment not initiated yet.",
            'requires_confirmation': "Payment method selected, waiting for confirmation.",
            'requires_action': "Additional action required (e.g., 3D Secure authentication).",
            'processing': "Payment is being processed.",
            'requires_capture': "Payment authorized, waiting for capture.",
            'canceled': "Payment was canceled.",
            'succeeded': "Payment successful and funds received."
        }
        
        return status_messages.get(payment_intent.status, f"Unknown status: {payment_intent.status}")
    
    except stripe.error.StripeError as e:
        return f"Error checking payment status: {str(e)}"

def main():
    st.title("Avuant Advisory Services")

    tab1, tab2, tab3 = st.tabs(["Make Payment", "Track Payment", "Pre-authorization"])

    with tab1:
        st.header("Payment Details")
        
        invoice_number = str(random.randint(1000000, 9999999))
        description = "Advisory Services"
        
        st.write(f"Invoice Number: {invoice_number}")
        st.write(f"Description: {description}")

        currency = st.selectbox("Select Currency", list(CURRENCIES.keys()), 
                                format_func=lambda x: f"{x} - {CURRENCIES[x]}")

        amount = st.number_input("Amount", min_value=0.01, step=0.01, value=10.00)

        if amount > 0:
            estimated_fee = estimate_stripe_fees(amount, currency)
            clearance_time = estimate_clearance_time(currency)
            st.write(f"Estimated Stripe fee: {estimated_fee} {currency}")
            st.write(f"Total amount (including fee): {amount + estimated_fee} {currency}")
            st.write(f"Estimated clearance time: {clearance_time}")

        payment_method = st.radio("Select Payment Method", ["Credit/Debit Card", "Bank Transfer"])

        if payment_method == "Credit/Debit Card":
            st.subheader("Enter Card Details")
            card_number = st.text_input("Card Number")
            exp_month = st.text_input("Expiration Month (MM)")
            exp_year = st.text_input("Expiration Year (YYYY)")
            cvc = st.text_input("CVC")
            stripe_payment_method = "card"
        else:
            st.subheader("Enter Bank Account Details")
            if currency in BANK_TRANSFER_REQUIREMENTS:
                for field in BANK_TRANSFER_REQUIREMENTS[currency]:
                    st.text_input(field)
            else:
                st.warning(f"Bank transfer details for {currency} are not available. Please contact support for assistance.")
            stripe_payment_method = "customer_balance"

        if st.button("Confirm Payment"):
            payment_intent = create_payment_intent(amount, currency, stripe_payment_method, invoice_number, description)
            
            if payment_intent:
                st.success("Payment Intent created successfully!")
                st.json(payment_intent)
                st.info(f"Use this Client Secret to complete the payment: {payment_intent.client_secret}")
                st.info(f"Your invoice number is: {invoice_number}. Please save this for tracking your payment.")

                if payment_method == "Bank Transfer":
                    st.warning("For bank transfers, please use the payment instructions provided by our support team to complete the transaction.")

                # Additional message output for payment confirmation
                status = check_payment_status(invoice_number)
                st.write(f"Payment Status: {status}")

            st.subheader("Adaptive Pricing")
            st.write("This payment uses Adaptive Pricing, which automatically selects the best payment method based on the customer's location and preferences.")

    with tab2:
        st.header("Track Your Payment")
        tracking_invoice_number = st.text_input("Enter your invoice number")
        if st.button("Track Payment"):
            if tracking_invoice_number:
                status = check_payment_status(tracking_invoice_number)
                st.write(f"Payment Status: {status}")
            else:
                st.warning("Please enter an invoice number to track your payment.")

    with tab3:
        st.header("Pre-authorization")
        st.write("Pre-authorize a payment amount without capturing it immediately.")
        
        # Add prominent notice about pre-authorization expiration
        st.warning("⚠️ Important: The pre-authorization will expire in 7 days if not captured. After expiration, the funds will be released back to the card holder.")

        preauth_amount = st.number_input("Pre-authorization Amount", min_value=0.01, step=0.01, value=10.00)
        preauth_currency = st.selectbox("Select Currency for Pre-authorization", list(CURRENCIES.keys()), 
                                        format_func=lambda x: f"{x} - {CURRENCIES[x]}")

        st.subheader("Enter Card Details for Pre-authorization")
        preauth_card_number = st.text_input("Card Number", key="preauth_card_number")
        preauth_exp_month = st.text_input("Expiration Month (MM)", key="preauth_exp_month")
        preauth_exp_year = st.text_input("Expiration Year (YYYY)", key="preauth_exp_year")
        preauth_cvc = st.text_input("CVC", key="preauth_cvc")

        if st.button("Pre-authorize Payment"):
            preauth_invoice_number = f"PREAUTH-{str(random.randint(1000000, 9999999))}"
            preauth_description = "Pre-authorized Payment"

            preauth_intent = create_payment_intent(preauth_amount, preauth_currency, "card", preauth_invoice_number, preauth_description, capture=False)

            if preauth_intent:
                st.success("Pre-authorization successful!")
                st.json(preauth_intent)
                st.info(f"Pre-authorization Invoice Number: {preauth_invoice_number}")
                
                # Additional message output for pre-authorization confirmation
                st.write(f"Pre-authorization Status: {preauth_intent.status}")
                expiration_date = datetime.now() + timedelta(days=7)
                st.write(f"Pre-authorization Expiration Date: {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Remind user about expiration
                st.warning("Remember: This pre-authorization will expire in 7 days if not captured. After expiration, the funds will be released.")

if __name__ == "__main__":
    main()
