import streamlit as st
import random

# Configuración de la página
st.set_page_config(page_title="Ecuaciones de Primer Grado", page_icon="🧮")

st.title("🧮 Resolución de ecuaciones de primer grado")

# --- Función para generar una nueva ecuación con solución entera ---
def generar_ecuacion():
    a = random.randint(1, 10)
    x_sol = random.randint(-10, 10)
    b = random.randint(-10, 10)
    c = a * x_sol + b
    return a, b, c, x_sol

# Inicializar variables en session_state
if "a" not in st.session_state:
    st.session_state.a, st.session_state.b, st.session_state.c, st.session_state.x_sol = generar_ecuacion()
if "resultado" not in st.session_state:
    st.session_state.resultado = None
if "respuesta_correcta" not in st.session_state:
    st.session_state.respuesta_correcta = False

# Mostrar la ecuación actual
st.markdown(f"### 👉 Resuelve la ecuación: **{st.session_state.a}·x + {st.session_state.b} = {st.session_state.c}**")

# Entrada del usuario
respuesta = st.number_input("Tu respuesta (entero):", step=1, format="%d")

# Botón para comprobar la respuesta
if st.button("Comprobar respuesta"):
    if respuesta == st.session_state.x_sol:
        st.session_state.resultado = "✅ ¡Correcto!"
        st.session_state.respuesta_correcta = True
        st.balloons()
    else:
        st.session_state.resultado = "❌ Incorrecto, inténtalo de nuevo."
        st.session_state.respuesta_correcta = False

# Mostrar resultado si ya se comprobó
if st.session_state.resultado:
    if st.session_state.respuesta_correcta:
        st.success(st.session_state.resultado)
    else:
        st.error(st.session_state.resultado)

# Botón para pasar a la siguiente ecuación (solo aparece después de comprobar)
if st.session_state.resultado:
    if st.button("➡️ Siguiente ecuación"):
        st.session_state.a, st.session_state.b, st.session_state.c, st.session_state.x_sol = generar_ecuacion()
        st.session_state.resultado = None
        st.session_state.respuesta_correcta = False
        st.experimental_rerun()
