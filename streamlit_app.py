import streamlit as st
import stripe
from datetime import datetime, timedelta

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

# Updated currencies supported by Stripe
CURRENCIES = {
    "USD": "United States Dollar",
    "EUR": "Euro",
    "GBP": "British Pound Sterling",
    "JPY": "Japanese Yen",
    "CAD": "Canadian Dollar",
    "AUD": "Australian Dollar",
    "CHF": "Swiss Franc",
    "CNY": "Chinese Yuan",
    "HKD": "Hong Kong Dollar",
    "SGD": "Singapore Dollar"
}

def get_account_balance():
    try:
        balance = stripe.Balance.retrieve()
        return {avail_balance.currency.upper(): avail_balance.amount / 100 for avail_balance in balance.available}
    except stripe.error.StripeError as e:
        st.error(f"Error retrieving account balance: {str(e)}")
        return None

def estimate_stripe_fees(amount, currency):
    try:
        # For simplicity, we're using a fixed rate here. In reality, Stripe's fees can vary.
        if currency == 'USD':
            return round(amount * 0.029 + 0.30, 2)  # 2.9% + $0.30 for US transactions
        else:
            return round(amount * 0.039 + 0.30, 2)  # 3.9% + $0.30 for international transactions
    except Exception as e:
        st.error(f"Error estimating fees: {str(e)}")
        return None

def estimate_clearance_time(currency):
    # This is a simplified estimation. In reality, it depends on various factors.
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

def create_payment_intent(amount, currency, payment_method_id=None, payment_method_types=None):
    try:
        intent_params = {
            "amount": int(amount * 100),  # Stripe uses cents
            "currency": currency,
            "payment_method_types": payment_method_types or ["card"],
        }
        if payment_method_id:
            intent_params["payment_method"] = payment_method_id
            intent_params["confirm"] = True

        payment_intent = stripe.PaymentIntent.create(**intent_params)
        return payment_intent
    except stripe.error.StripeError as e:
        st.error(f"Error creating PaymentIntent: {str(e)}")
        return None

def create_bank_account_token(country, currency, account_holder_name, account_number, routing_number):
    try:
        token = stripe.Token.create(
            bank_account={
                "country": country,
                "currency": currency,
                "account_holder_name": account_holder_name,
                "account_holder_type": "individual",
                "account_number": account_number,
                "routing_number": routing_number,
            },
        )
        return token
    except stripe.error.StripeError as e:
        st.error(f"Error creating bank account token: {str(e)}")
        return None

def main():
    st.title("Stripe Payment App (Multi-Currency)")

    # Fetch account balance at the start
    account_balance = get_account_balance()
    if not account_balance:
        st.error("Unable to retrieve account balance. Please try again later.")
        return

    currency = st.selectbox("Currency", list(CURRENCIES.keys()), 
                            index=list(CURRENCIES.keys()).index('USD'),
                            format_func=lambda x: f"{x} - {CURRENCIES[x]}")
    amount = st.number_input("Amount", min_value=0.01, step=0.01)

    if amount > 0:
        estimated_fee = estimate_stripe_fees(amount, currency)
        clearance_time = estimate_clearance_time(currency)
        max_daily_payment = account_balance.get(currency, 0)

        st.subheader("Payment Information")
        st.write(f"Amount to be paid: {amount} {currency}")
        st.write(f"Estimated Stripe fee: {estimated_fee} {currency}")
        st.write(f"Estimated clearance time: {clearance_time}")
        st.write(f"Available balance for payouts: {max_daily_payment} {currency}")

        if amount > max_daily_payment:
            st.warning(f"The amount exceeds the available balance of {max_daily_payment} {currency}")
        else:
            st.success("The amount is within the available balance")

        st.write("Note: Additional fees and charges may be incurred by your bank or card issuer.")

        payment_method = st.radio("Choose payment method:", ("Credit/Debit Card", "Bank Transfer"))

        if payment_method == "Credit/Debit Card":
            st.subheader("Enter Card Details")
            card_number = st.text_input("Card Number")
            exp_month = st.text_input("Expiration Month (MM)")
            exp_year = st.text_input("Expiration Year (YYYY)")
            cvc = st.text_input("CVC")

            if st.button("Make Card Payment"):
                try:
                    payment_method = stripe.PaymentMethod.create(
                        type="card",
                        card={
                            "number": card_number,
                            "exp_month": exp_month,
                            "exp_year": exp_year,
                            "cvc": cvc,
                        },
                    )

                    payment_intent = create_payment_intent(amount, currency, payment_method.id)
                    
                    if payment_intent:
                        st.info(f"Payment status: {payment_intent.status}")
                        st.info(f"Payment Intent ID: {payment_intent.id}")
                except stripe.error.CardError as e:
                    st.error(f"Card error: {e.error.message}")
                except stripe.error.StripeError as e:
                    st.error(f"Stripe error: {str(e)}")

        else:  # Bank Transfer
            st.subheader("Enter Bank Account Details")
            account_holder_name = st.text_input("Account Holder Name")
            account_number = st.text_input("Account Number")
            routing_number = st.text_input("Routing Number")

            if st.button("Make Bank Transfer"):
                try:
                    country = "US" if currency == "USD" else "EU"
                    bank_token = create_bank_account_token(country, currency, account_holder_name, account_number, routing_number)

                    if bank_token:
                        payment_method_types = ["ach_debit"] if currency == "USD" else ["sepa_debit"]
                        payment_intent = create_payment_intent(amount, currency, bank_token.id, payment_method_types)
                        
                        if payment_intent:
                            st.info(f"Payment status: {payment_intent.status}")
                            st.info(f"Payment Intent ID: {payment_intent.id}")
                except stripe.error.StripeError as e:
                    st.error(f"Stripe error: {str(e)}")

if __name__ == "__main__":
    main()
