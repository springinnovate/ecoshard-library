# Install GeoServer
FROM therealspring/python-gdal:3.0.4

RUN apt-get update -qq && \
    apt-get install -y \
    openjdk-11-jdk-headless \
    openjdk-11-jdk \
    libspatialindex-dev \
    postgresql-client \
    curl \
    git \
    && \
    rm -rf /var/lib/apt/lists/*

SHELL ["/bin/bash", "-c"]
WORKDIR /usr/local

RUN useradd -r -m -U -d /opt/tomcat -s /bin/false tomcat
COPY apache-tomcat-9.0.36.tar.gz .
RUN tar xzvf apache-tomcat-9.0.36.tar.gz -C /opt/tomcat --strip-components=1 && rm apache-tomcat-9.0.36.tar.gz
RUN chgrp -R tomcat /opt/tomcat && \
    chmod -R g+r /opt/tomcat/conf && \
    chmod g+x /opt/tomcat/conf && \
    chown -R tomcat /opt/tomcat/webapps/ /opt/tomcat/work/ /opt/tomcat/temp/ /opt/tomcat/logs/

COPY geoserver-2.17.1-war.zip .
RUN unzip geoserver-2.17.1-war.zip geoserver.war -d /opt/tomcat/webapps/ && rm geoserver-2.17.1-war.zip

RUN /opt/tomcat/bin/catalina.sh start && sleep 15 && /opt/tomcat/bin/catalina.sh stop

COPY start_geoserver.sh /usr/local/bin/

EXPOSE 8080
ENTRYPOINT ["bash",  "-i", "/usr/local/bin/start_geoserver.sh"]
