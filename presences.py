import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Fusionnator de présences",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="auto",
)

PRESENT = "1"
ABSENT = "ABS"
NA_FILL = "NA"
PAS_PRISE = "-"
CERTIFICAT = "C"

uploaded_files = st.file_uploader("Choose a file", accept_multiple_files=True)

if uploaded_files:
    dataframes, actas = [], {"id": [], "name": [], "group": []}

    for uploaded_file in uploaded_files:
        
        file_name = uploaded_file.name
        acta_id, acta_name, acta_group = [s.strip("_ ") for s in file_name.split("-")]
        acta_group = acta_group.split(".")[0].strip("_ ")
        actas["id"].append(acta_id)
        actas["name"].append(acta_name)
        actas["group"].append(acta_group)
        dataframes.append(
            pd.read_excel(
                uploaded_file, 
                sheet_name="Toutes les présences", 
                parse_dates=["Horaire"],
                usecols=["Matricule", "Nom", "Prénom", "Statut", "Horaire", "Présence"],
            ).assign(Groupe=acta_group)
        )


    dataframe = pd.concat(dataframes, ignore_index=True)
    df_actas = pd.DataFrame(actas)
    
    if len(df_actas["id"].unique()) > 1:
        st.warning("Attention, vous avez importé les présences de plusieurs ACTA. L'application ne gère pour l'instant correctement qu'une ACTA à la fois.")
        with st.expander("Afficher les ACTA importées"):
            st.dataframe(df_actas, use_container_width=True)

    st.header(f"Présences pour : {df_actas['id'][0]} - {df_actas['name'][0]}".replace("_", " ", -1))
    st.subheader(f"Groupes : {', '.join(df_actas['group'])}")

    legende = {"Symbole":[PRESENT, ABSENT, CERTIFICAT, PAS_PRISE, NA_FILL], "Signification": ["présent","absent","certificat", "présence pas prise", "pas de séance pour cet étudiant à cette date"]}
    st.markdown("**Légende**")
    st.table(pd.DataFrame(legende).set_index('Symbole').rename_axis('Symbole'))

    dataframe["Jour"] = dataframe["Horaire"].apply(lambda dt: dt.date())
    dataframe["Heure"] = dataframe["Horaire"].apply(lambda dt: dt.time().strftime('%H:%M'))
    dataframe["Horaire"] = dataframe["Horaire"].dt.strftime('%m/%d/%Y - %H:%M')

    dataframe["Nom complet"] = dataframe["Nom"] + " " + dataframe["Prénom"]  

    dataframe["Présence"] = dataframe["Présence"].apply(lambda p: PAS_PRISE if p=="." else p)  

    cols_order = ["Matricule", "Nom", "Prénom", "Groupe", "Jour", "Heure", "Présence", "Statut"]

    dataframe.drop_duplicates(subset=["Matricule", "Jour"], inplace=True)
    dataframe["Présence"] = dataframe["Présence"].replace({"1": PRESENT, "0": ABSENT, "c": CERTIFICAT})

    with st.expander("Afficher toutes les présences"):
        df = (
            dataframe.pivot_table(values='Présence', index=["Matricule", "Nom", "Prénom", "Groupe"], columns='Jour', aggfunc='first')
            .fillna(NA_FILL)
        )
        st.dataframe(df)
    
    @st.cache_data
    def convert_df(df):
        return df.to_csv().encode('utf-8')

    df_csv = convert_df(df)
    st.download_button(
        label="Télécharger les présences complètes en csv",
        data=df_csv,
        file_name=f'{df_actas["name"][0]}.csv',
        mime='text/csv',
    )

    student = st.selectbox(
        'De quel étudiant voulez-vous connaître les présences ?',
        dataframe["Nom complet"].unique(),
    )

    if student:    
        st.write(f'Votre choix : {student}')
        # perc = dataframe["Présence"].value_counts(normalize=True)["1"] * 100
        # st.metric("Pourcentage de présence", f"{round(perc, 2)} %", )
        col1, col2 = st.columns(2)
        filter_name = (dataframe["Nom complet"] == student)
        filter_present = dataframe["Présence"].isin([PRESENT, CERTIFICAT, PAS_PRISE])
        filter = filter_name & filter_present
        col1.dataframe(
            dataframe.loc[filter, cols_order],
            use_container_width=True,
        )

        fig = px.pie(
            dataframe.loc[filter_name, "Présence"],
            names="Présence", 
        )

        fig.update_traces(hoverinfo='percent', textinfo='label+percent')

        col2.plotly_chart(fig, use_container_width=True)