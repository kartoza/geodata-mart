FROM 3liz/qgis-wps:ltr-rc as wps

# FROM wps as wps-build-stage

# # Install qgis

# RUN apt install gnupg software-properties-common
# RUN wget -qO - https://qgis.org/downloads/qgis-2021.gpg.key | sudo gpg --no-default-keyring --keyring gnupg-ring:/etc/apt/trusted.gpg.d/qgis-archive.gpg --import
# RUN chmod a+r /etc/apt/trusted.gpg.d/qgis-archive.gpg
# RUN add-apt-repository "deb https://qgis.org/ubuntu $(lsb_release -c -s) main"
# RUN apt update && apt install qgis qgis-plugin-grass

# FROM wps-build-stage as qgis

# ----------------------------------------

# Swap out volume locations for symlinks
# so that a single named volume can be used

RUN mkdir -p /data/processing
RUN ln -s /data/processing /processing

RUN mkdir -p /data/projects
RUN ln -s /data/projects /projects

RUN mkdir -p /data/workdir
RUN ln -s /data/workdir /srv/data

ENTRYPOINT ["/docker-entrypoint.sh"]
