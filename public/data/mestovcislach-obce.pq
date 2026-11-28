// mestovcislach.sk – všetky obce a ukazovatele Dátového štúdia (Power Query / jazyk M)
// Power BI: Získať údaje → Prázdny dotaz → Rozšírený editor → vložiť. Excel: Údaje → Získať údaje → Z iných zdrojov → Prázdny dotaz.
let
    Zdroj = Csv.Document(
        Web.Contents("https://mestovcislach.sk/data/obce-ukazovatele.csv"),
        [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Hlavicky = Table.PromoteHeaders(Zdroj, [PromoteAllScalars = true]),
    // prvých 5 stĺpcov je text (kód, obec, okres, kraj, adresa), ostatné sú čísla s desatinnou čiarkou
    CiselneStlpce = List.Skip(Table.ColumnNames(Hlavicky), 5),
    Typy = Table.TransformColumnTypes(
        Hlavicky,
        List.Combine({
            {{"kod_obce", type text}, {"obec", type text}, {"okres", type text}, {"kraj", type text}, {"url", type text}},
            List.Transform(CiselneStlpce, each {_, type number})
        }),
        "sk-SK"
    )
in
    Typy
