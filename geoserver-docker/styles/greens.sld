<?xml version="1.0" encoding="ISO-8859-1"?>
<StyledLayerDescriptor version="1.0.0"
    xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NamedLayer>
    <Name>greens</Name>
    <UserStyle>
      <Title>greens</Title>
      <FeatureTypeStyle>
        <Rule>
          <RasterSymbolizer>
            <ColorMap>
              <ColorMapEntry quantity="${env('p0', 0.0)}" label="${env('p0', 0.0)}" color="#f7fcf5"/>
              <ColorMapEntry quantity="${env('p50', 0.5)}" label="${env('p50', 0.5)}" color="#74c476"/>
              <ColorMapEntry quantity="${env('p100', 010)}" label="${env('p100', 1.0)}" color="#00441b"/>
            </ColorMap>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>