# Bibliotecas estándar de Python
import json

# Manipulación de datos y geometrías
import pandas as pd
import geopandas as gpd
import numpy as np

# Manejo de imágenes
from PIL import Image

# Integración web y aplicaciones interactivas
import streamlit as st
import streamlit_google_oauth as oauth
from streamlit_vertical_slider import vertical_slider
import plotly.graph_objects as go

# Manejo de geometrías
from shapely.geometry import shape, mapping, Point

# Procesamiento de imágenes y datos raster
import rasterio
from rasterio.features import shapes, geometry_mask

# Interpolación y análisis espacial
from scipy.interpolate import RBFInterpolator

# Earth Engine y mapeo avanzado
import ee
import geemap.foliumap as geemap

# Módulos o paquetes locales
from helper import translate, api_call_logo, decrypt_token, api_call_fields, domains_areas_by_user, seasons, farms
from secretManager import AWSSecret
import logging

###################################################################################

def main_app(user_info):
    #########################################################################################################################
    # Page Config y estilo
    #########################################################################################################################

    st.set_page_config(
        page_title="Benchmarking",
        page_icon=Image.open("assets/favicon geoagro nuevo-13.png"),
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://geoagro1.atlassian.net/servicedesk/customer/portal/5',
            'Report a bug': "https://geoagro1.atlassian.net/servicedesk/customer/portal/5",
            'About': "Powered by GeoAgro"
        }
    )

    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    
    ##################### USER INFO #####################

    language = user_info['language']
    email = user_info['email']
    env = user_info['env']
    st.session_state['env'] = env

    ##################### API Logo Marca Blanca #####################
        
    # secrets = None
    # access_key_id = st.secrets["API_key"]
    if env == 'test':
        secrets = json.loads(AWSSecret().get_secret(secret_name="test/apigraphql360", region_name="us-west-2"))
    elif env == 'prod':
        secrets = json.loads(AWSSecret().get_secret(secret_name="prod/apigraphql360-v2", region_name="us-west-2"))

    access_key_id = secrets['x-api-key']
    url = secrets['url']
    
    @st.cache_data
    def get_logo(user_info, access_key_id, url, default_logo_path):
        logo_image = api_call_logo(user_info, access_key_id,  url, default_logo_path)
        return logo_image

    logo_image = get_logo(user_info, access_key_id, url, default_logo_path='assets/GeoAgro_principal.png')
    st.session_state['logo_image'] = logo_image

    ##################### LANGUAGE  #####################

    c_1, c_2, c_3 = st.columns([1.5, 4.5, 1], gap="small")

    with c_1:
        st.image(logo_image)

    with c_3:   
        try:
            langs = ['es', 'en', 'pt']
            if language is not None:
                lang = st.selectbox(translate("language", language), label_visibility="hidden", options=langs, index=langs.index(language))
            else:  # from public link
                lang = st.selectbox(translate("es", language), label_visibility="hidden", options=langs)
            
            st.session_state['lang'] = lang
        except Exception as exception:
            lang = "es"
            st.session_state['lang'] = lang
            pass

    ##################### Titulo / solicitado por  #####################

    # st.subheader(translate("dashboards",lang), anchor=False)
    st.markdown(f'{translate("requested_by",lang)}<a style="color:blue;font-size:18px;">{""+email+""}</a> | <a style="color:blue;font-size:16px;" target="_self" href="/"> {translate("logout",lang)}</a>', unsafe_allow_html=True)
    st.markdown('')
    st.markdown('')

    with st.sidebar:
        ############################################################################
        # DOMAIN
        ############################################################################

        hay_algun_establecimiento_seleccionado=False

        # Función para realizar la llamada a la API y cachear la respuesta
        @st.cache_data
        def get_domains_areas_by_user(user_info, access_key_id, url):
            api_call = domains_areas_by_user(user_info['email'], access_key_id, url)
            return api_call
        
        # Obtener la información de dominio
        dominios_api = get_domains_areas_by_user(user_info, access_key_id, url)

        # Filtrar y ordenar los dominios
        dominios_filtrados_ordenados = sorted([dominio for dominio in dominios_api if not dominio['deleted']], key=lambda dominio: dominio['name'])

        # Intentar encontrar el índice del dominio predeterminado en user_info
        default_domain_index = next((index for index, dominio in enumerate(dominios_filtrados_ordenados) if dominio['id'] == user_info['domainId']), None)

        # Selector de dominio en Streamlit
        dominio_seleccionado_nombre = st.selectbox(translate("domain",lang), [dominio['name'] for dominio in dominios_filtrados_ordenados], index=default_domain_index)
        dominio_seleccionado = next((dominio for dominio in dominios_filtrados_ordenados if dominio['name'] == dominio_seleccionado_nombre), None)

        ############################################################################
        # AREA
        ############################################################################

        if dominio_seleccionado:
            # Obtener áreas del dominio seleccionado y filtrarlas
            areas_seleccionadas = dominio_seleccionado['areas']
            areas_filtradas_ordenadas = sorted([area for area in areas_seleccionadas if not area['deleted']], key=lambda area: area['name'])

            # Añadir un área ficticia al inicio
            area_ficticia = {'name': '--', 'id': 0}
            areas_filtradas_ordenadas.insert(0, area_ficticia)

            # Intentar encontrar el índice del área predeterminada en user_info
            default_area_index = next((index for index, area in enumerate(areas_filtradas_ordenadas) if area['id'] == user_info['areaId']), None)
            # Asegurarse de que el índice no sea None para el área ficticia
            if default_area_index is None:
                default_area_index = 0  # Esto seleccionará el área ficticia por defecto si no se encuentra otra área predeterminada

            # Selector de área en Streamlit
            area_seleccionada_nombre = st.selectbox(translate("area", lang), [area['name'] for area in areas_filtradas_ordenadas], index=default_area_index)
            area_seleccionada = next((area for area in areas_filtradas_ordenadas if area['name'] == area_seleccionada_nombre), None)


            ############################################################################
            # WORWSPACE
            ############################################################################

            if area_seleccionada:
                if area_seleccionada['id'] != 0:
                    # Obtener workspaces del área seleccionada y filtrarlos
                    workspaces_seleccionados = area_seleccionada['workspaces']

                if area_seleccionada['id'] == 0:
                    # Obtener workspaces del área seleccionada y filtrarlos
                    workspaces_seleccionados = dominio_seleccionado['workspaces']

                workspaces_filtrados_ordenados = sorted([workspace for workspace in workspaces_seleccionados if not workspace['deleted']], key=lambda workspace: workspace['name'])

                # Intentar encontrar el índice del workspace predeterminado en user_info
                default_workspace_index = next((index for index, workspace in enumerate(workspaces_filtrados_ordenados) if workspace['id'] == user_info['workspaceId']), None)

                # Selector de workspace en Streamlit
                workspace_seleccionado_nombre = st.selectbox(translate("workspace",lang), [workspace['name'] for workspace in workspaces_filtrados_ordenados], index=default_workspace_index)
                workspace_seleccionado = next((workspace for workspace in workspaces_filtrados_ordenados if workspace['name'] == workspace_seleccionado_nombre), None)

                ############################################################################
                # Season
                ############################################################################

                # Función para realizar la llamada a la API y cachear la respuesta
                @st.cache_data
                def get_seasons(workspaceId, access_key_id, url):
                    api_call = seasons(workspaceId, access_key_id, url)
                    return api_call
                
                # Si se seleccionó un workspace, obtener las temporadas para ese workspace
                if workspace_seleccionado:
                    # Realizar la llamada a la API para obtener las temporadas del workspace seleccionado
                    seasons_data = get_seasons(workspace_seleccionado['id'], access_key_id, url)

                    # Filtrar y ordenar las temporadas que no están eliminadas
                    seasons_filtradas_ordenadas = sorted([season for season in seasons_data if not season['deleted']], key=lambda season: season['name'])

                    # Intentar encontrar el índice de la temporada predeterminada en user_info
                    default_season_index = next((index for index, season in enumerate(seasons_filtradas_ordenadas) if season['id'] == user_info['seasonId']), None)

                    # Selector de temporada en Streamlit
                    season_seleccionada_nombre = st.selectbox(translate("season",lang), [season['name'] for season in seasons_filtradas_ordenadas], index=default_season_index)
                    season_seleccionada = next((season for season in seasons_filtradas_ordenadas if season['name'] == season_seleccionada_nombre), None)

                    ############################################################################
                    # Farm
                    ############################################################################

                    # Función para realizar la llamada a la API y cachear la respuesta
                    @st.cache_data
                    def get_farms(workspaceId, seasonId, access_key_id, url):
                        api_call = farms(workspaceId, seasonId, access_key_id, url)
                        return api_call

                    # Si se seleccionó una temporada, obtener las granjas para esa temporada y workspace
                    if season_seleccionada:
                        # Realizar la llamada a la API para obtener las granjas del workspace y la temporada seleccionados
                        farms_data = get_farms(workspace_seleccionado['id'], season_seleccionada['id'], access_key_id, url)

                        # Filtrar y ordenar las granjas que no están eliminadas
                        farms_filtradas_ordenadas = sorted([farm for farm in farms_data if not farm['deleted']], key=lambda farm: farm['name'])

                        # Intentar encontrar el índice de la granja predeterminada en user_info
                        default_farm_index = next((index for index, farm in enumerate(farms_filtradas_ordenadas) if farm['id'] == user_info['farmId']), None)

                        farm_seleccionada_nombre = st.selectbox(translate("farm",lang), [farm['name'] for farm in farms_filtradas_ordenadas], index=default_farm_index)
                        farm_seleccionada = next((farm for farm in farms_filtradas_ordenadas if farm['name'] == farm_seleccionada_nombre), None)

                        if farm_seleccionada:
                            hay_algun_establecimiento_seleccionado=True
                        
        ############################################################################
        # Powered by GeoAgro Picture
        ############################################################################
        st.markdown('')
        st.markdown('')
        st.markdown('')

        st.markdown(
            """
            <style>
                div [data-testid=stImage]{
                    bottom:0;
                    display: flex;
                    margin-bottom:10px;
                }
            </style>
            """, unsafe_allow_html=True
            )
            
        
        cI1,cI2,cI3=st.columns([1,4,1], gap="small")
        with cI1:
            pass
        with cI2:
            image = Image.open('assets/Powered by GeoAgro-01.png')
            new_image = image.resize((220, 35))
            st.image(new_image)
        with cI3:
            pass

    ############################################################################

    if hay_algun_establecimiento_seleccionado == True:

        ############################################################################
        # LOTES
        ############################################################################

        # Función para realizar la llamada a la API y cachear la respuesta
        @st.cache_data
        def get_fields(seasonId, farmId, lang, url, access_key_id):
            df = api_call_fields(seasonId, farmId, lang, url, access_key_id)
            return df

        # Llamar a la función get_fields_table que está cacheada
        filtered_df = get_fields(season_seleccionada['id'], farm_seleccionada['id'], lang, url, access_key_id)

        # Convertir la columna 'geometry' de GeoJSON a geometrías de Shapely
        def geojson_to_geometry(geojson_str):
            if geojson_str is not None:
                geojson = json.loads(geojson_str)
                return shape(geojson)
            return None

        filtered_df['geometry'] = filtered_df['geometry'].apply(geojson_to_geometry)

        # Eliminar la columna 'geometry' de GeoJSON ya que ya no es necesaria
        filtered_df = filtered_df.drop('geometryWKB', axis=1, errors='ignore')  # Usamos errors='ignore' para evitar errores si la columna no existe

        # Convertir el DataFrame de Pandas a un GeoDataFrame de GeoPandas
        gdf_poly = gpd.GeoDataFrame(filtered_df, geometry='geometry')

        # Nombres de columnas originales y sus nuevos nombres
        renombrar_columnas = {
            "crop_name": "crop",
            "hybrid_name": "hybrid",
            "has": "hectares",
            "name": translate("field",lang),
        }

        # Filtrar y mantener solo las columnas que necesitan ser renombradas
        columnas_para_renombrar = {orig: nuevo for orig, nuevo in renombrar_columnas.items() if orig in gdf_poly.columns}

        # Renombrar columnas del GeoDataFrame
        gdf_poly = gdf_poly.rename(columns=columnas_para_renombrar)

        # Paso 1: Eliminar filas donde 'hectares' es nulo
        gdf_poly = gdf_poly.dropna(subset=['hectares'])

        # Paso 2: Eliminar filas donde 'hectares' es 0
        gdf_poly = gdf_poly[gdf_poly['hectares'] != 0]

        # Disolver geometrías por 'field_name', sumar los 'hectares' y mantener 'field_name'
        gdf_poly = gdf_poly.dissolve(by=translate("field",lang), aggfunc={'hectares': 'sum'}).reset_index()

        ############################################################################
        # Mapa
        ############################################################################

        ################ Titulo ################

        st.markdown('')
        st.markdown('')
        st.markdown(f"<b>{'NASA SRTM Digital Elevation Model'} </b>", unsafe_allow_html=True, help='https://developers.google.com/earth-engine/datasets/catalog/USGS_SRTMGL1_003')
    
        ############################################################################
        # TAB 1
        ############################################################################

        import ee  # Import the Earth Engine module

        # Crea una instancia de la clase AWSSecret y obtén el secreto para GEE
        gee_secrets = json.loads(AWSSecret().get_secret(secret_name="prod/streamlit/gee", region_name="us-east-1"))

        # Extrae client_email y la clave privada del secreto
        client_email = gee_secrets['client_email']
        private_key = gee_secrets['private_key']  # Asegúrate de que 'private_key' es el nombre correcto del campo en tu secreto

        # Configura las credenciales y inicializa Earth Engine
        credentials = ee.ServiceAccountCredentials(client_email, key_data=private_key)
        ee.Initialize(credentials)

        from ndvi import extract_mean_ndvi_date
        
        # DataFrame final que almacenará los resultados
        final_df = pd.DataFrame()

        for index, row in gdf_poly.iterrows():
            # Extraer la geometría individual
            lote_gdf_filtrado = gdf_poly.iloc[[index]]
            
            # Llamar a la función con la geometría actual
            df_temp = extract_mean_ndvi_date(lote_gdf_filtrado)
            
            # Obtener el nombre de la geometría
            geom_name = row[translate("field", lang)]
            
            # Agregar el nombre de la geometría como columna
            df_temp[translate("field", lang)] = geom_name
            
            # Agregar el DataFrame temporal al DataFrame final
            final_df = pd.concat([final_df, df_temp], ignore_index=True)

            # Asumiendo que tu DataFrame se llama df
            pivot_df = final_df.pivot_table(index='Date', columns='Lote', values='Mean_NDVI')

            # Opcionalmente, puedes resetear el índice si prefieres que la fecha sea una columna regular en lugar de el índice del DataFrame
            pivot_df.reset_index(inplace=True)

        # Mostrar el DataFrame final
        st.dataframe(pivot_df)

        import plotly.express as px

        # Convertir la columna 'Date' a datetime si aún no lo es
        pivot_df['Date'] = pd.to_datetime(pivot_df['Date'])

        # Convertir las fechas a un formato numérico (por ejemplo, el número de días desde la primera fecha)
        pivot_df['DateNum'] = (pivot_df['Date'] - pivot_df['Date'].min()) / np.timedelta64(1, 'D')

        # Preparar un nuevo DataFrame para almacenar los resultados interpolados
        interpolated_df = pd.DataFrame()
        interpolated_df['Date'] = pivot_df['Date']

        for column in pivot_df.columns:
            if column not in ['Date', 'DateNum']:
                # Filtrar los valores nulos y preparar los datos para la interpolación
                x = pivot_df.loc[pivot_df[column].notna(), 'DateNum']
                y = pivot_df.loc[pivot_df[column].notna(), column]
                
                # Crear el interpolador RBF
                rbf = RBFInterpolator(x[:, None], y, kernel='thin_plate_spline')  # Puedes experimentar con diferentes kernels
                
                # Interpolar los valores para todas las fechas
                y_interp = rbf(pivot_df['DateNum'][:, None])
                
                # Almacenar los resultados en el DataFrame
                interpolated_df[column] = y_interp

        # Usar Plotly Express para crear el gráfico de líneas
        fig = px.line(interpolated_df, x='Date', y=interpolated_df.columns[1:], markers=True)

        # Actualizar layout del gráfico
        fig.update_layout(
            title='NDVI medio por lote a lo largo del tiempo',
            xaxis_title='Fecha',
            yaxis_title='NDVI medio',
            legend_title='Lote'
        )

        # Asumiendo el uso de Streamlit para mostrar el gráfico
        st.plotly_chart(fig, use_container_width=True)


############################################################################
# MAIN
############################################################################
                    
if __name__ == "__main__":
    redirect_uri=" http://localhost:8501"
    user_info = {'email': "mbonelli@geoagro.com", 'language': 'es', 'env': 'prod', 'domainId': 1, 'areaId': 11553, 'workspaceId': 1757, 'seasonId': 2588, 'farmId': 13510}
    main_app(user_info)


# if __name__ == "__main__":
#     redirect_uri = "https://dem.geoagro.com/"
#     user_info = None

#     try:
#         # Intentar obtener user_info de los tokens
#         token1 = st.query_params['token1']
#         token2 = st.query_params['token2']
#         user_info = decrypt_token(token1)  # Asumiendo que esta función existe y decodifica el token
#         st.session_state['user_info'] = user_info  # Guardar user_info en session_state
#     except Exception as e:
#         print(e)

#     if user_info is None:
#         # Intentar recuperar user_info de session_state si los tokens fallan
#         user_info = st.session_state.get('user_info')
#         print(user_info)

#         if user_info is None:
#             googleoauth_secrets = json.loads(AWSSecret().get_secret(secret_name="prod/streamlit-google-oauth", region_name="us-west-2"))
#             client_id = googleoauth_secrets['client_id']
#             client_secret = googleoauth_secrets['client_secret']

#             # Si user_info aún no está disponible, proceder con el flujo de login y usar la función domains_areas_by_user
#             login_info = oauth.login(
#                 client_id=client_id,
#                 client_secret=client_secret,
#                 redirect_uri=redirect_uri,
#             )
#             print('login_info: ', login_info)
            
#             if login_info:
#                 user_id, user_email = login_info
#                 user_info = {
#                     'email': user_email, 'language': 'es', 'env': 'prod', 'domainId': None,
#                     'areaId': None, 'workspaceId': None, 'seasonId': None, 'farmId': None
#                 }

#             else:
#                 logging.error("Not logged")

#     if user_info:
#         main_app(user_info)  # Llamar a la función principal de la aplicación con user_info
#     else:
#         st.error("Error accessing the app. Please contact an administrator.")