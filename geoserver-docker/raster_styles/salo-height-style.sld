<?xml version="1.0" encoding="ISO-8859-1"?>
<StyledLayerDescriptor version="1.0.0"
    xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NamedLayer>
    <Name>salo: height-style</Name>
    <UserStyle>
      <Title>salo: height-style</Title>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <ColorMap>
              <ColorMapEntry quantity="$env{'p0', 0)}" label="$env{'p0', 0)}" color="#ffffff"/>
              <ColorMapEntry quantity="$env{'p75', 18)}" label="$env{'p75', 18)}" color="#292663"/>
              <ColorMapEntry quantity="$env{'p98', 19)}" label="$env{'p98', 19)}" color="#fdb515"/>
              <ColorMapEntry quantity="$env{'p100', 20)}" label="$env{'p100', 20)}" color="#fdb515"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
