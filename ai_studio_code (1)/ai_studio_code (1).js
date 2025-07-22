import React from 'react';

const DataTable = ({ title, data, columns }) => {
    return (
        <div className="table-wrapper">
            <h3>{title}</h3>
            <table>
                <thead>
                    <tr>
                        {columns.map(col => <th key={col.key}>{col.name}</th>)}
                    </tr>
                </thead>
                <tbody>
                    {data.length > 0 ? (
                        data.map((row, index) => (
                            <tr key={index}>
                                {columns.map(col => (
                                    <td key={col.key}>
                                        {typeof row[col.key] === 'number' 
                                            ? row[col.key].toLocaleString() 
                                            : row[col.key]}
                                    </td>
                                ))}
                            </tr>
                        ))
                    ) : (
                        <tr>
                            <td colSpan={columns.length}>No data to display.</td>
                        </tr>
                    )}
                </tbody>
            </table>
        </div>
    );
};

export default DataTable;