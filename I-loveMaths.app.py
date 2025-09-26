import streamlit as st
import random

st.set_page_config(page_title="Ecuaciones de Primer Grado", page_icon="🧮")

st.title("🧮 Aplicativo para resolver ecuaciones de primer grado")

# --- Generar ecuación con solución entera ---
if "a" not in st.session_state:
    st.session_state.a = random.randint(1, 10)
    st.session_state.x_sol = random.randint(-10, 10)
    st.session_state.b = random.randint(-10, 10)
    st.session_state.c = st.session_state.a * st.session_state.x_sol + st.session_state.b

a = st.session_state.a
b = st.session_state.b
c = st.session_state.c
x_sol = st.session_state.x_sol

st.write(f"👉 Resuelve la ecuación: **{a}·x + {b} = {c}**")

# --- Entrada del usuario ---
respuesta = st.number_input("Escribe el valor de x (debe ser un entero):", step=1, format="%d")

# --- Verificación ---
if st.button("Verificar mi respuesta"):
    if respuesta == x_sol:
        st.success("✅ ¡Correcto! 🎉")
        st.balloons()
        # Reiniciar para generar nueva ecuación
        del st.session_state["a"]
    else:
        st.error("❌ Incorrecto, inténtalo de nuevo.")
