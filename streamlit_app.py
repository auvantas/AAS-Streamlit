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

def get_account_balance(currency):
    try:
        balance = stripe.Balance.retrieve()
        for available_balance in balance.available:
            if available_balance.currency.upper() == currency:
                return available_balance.amount / 100  # Convert cents to currency units
        return 0  # Return 0 if the currency is not found
    except stripe.error.StripeError as e:
        st.error(f"Error retrieving account balance: {str(e)}")
        return None

def estimate_stripe_fees(amount, currency):
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency=currency,
            payment_method_types=['card'],
        )
        # Immediately cancel the intent as we only need it for fee calculation
        stripe.PaymentIntent.cancel(intent.id)
        
        # The fee is usually available in the response
        if hasattr(intent, 'latest_charge'):
            charge = stripe.Charge.retrieve(intent.latest_charge)
            return charge.balance_transaction.fee / 100  # Convert cents to currency units
        else:
            # If fee is not available, provide an estimate
            if currency == 'USD':
                return round(amount * 0.029 + 0.30, 2)  # 2.9% + $0.30 for US transactions
            else:
                return round(amount * 0.039 + 0.30, 2)  # 3.9% + $0.30 for international transactions
    except stripe.error.StripeError as e:
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

def create_payment_intent(amount, currency, payment_method_id=None):
    try:
        intent_params = {
            "amount": int(amount * 100),  # Stripe uses cents
            "currency": currency,
            "payment_method_types": ["card"],
        }
        if payment_method_id:
            intent_params["payment_method"] = payment_method_id
            intent_params["confirm"] = True

        payment_intent = stripe.PaymentIntent.create(**intent_params)
        return payment_intent
    except stripe.error.StripeError as e:
        st.error(f"Error creating PaymentIntent: {str(e)}")
        return None

def main():
    st.title("Auvant Advisory Services")

    currency = st.selectbox("Currency", list(CURRENCIES.keys()), 
                            index=list(CURRENCIES.keys()).index('USD'),
                            format_func=lambda x: f"{x} - {CURRENCIES[x]}")
    amount = st.number_input("Amount", min_value=0.01, step=0.01)

    if st.button("Get Payment Information"):
        max_daily_payment = get_account_balance(currency)
        estimated_fee = estimate_stripe_fees(amount, currency)
        clearance_time = estimate_clearance_time(currency)

        st.subheader("Payment Information")
        st.write(f"Maximum daily payment: {max_daily_payment} {currency}")
        st.write(f"Estimated fee: {estimated_fee} {currency}")
        st.write(f"Estimated clearance time: {clearance_time}")

        if amount > max_daily_payment:
            st.warning(f"The amount exceeds the maximum daily payment of {max_daily_payment} {currency}")
        else:
            st.success("The amount is within the daily payment limit")

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
            st.warning("Bank transfer functionality is not implemented in this demo.")

if __name__ == "__main__":
    main()
